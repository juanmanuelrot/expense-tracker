"""Handlers for text, photo, and voice expense input + confirmation flow."""

import logging
import uuid
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.user import User
from app.models.account import Account
from app.models.card import Card
from app.services import ai_service, expense_service, audio_service, budget_service
from bot.keyboards import confirm_expense_keyboard, category_keyboard, account_keyboard

logger = logging.getLogger(__name__)


async def _get_user_context(db, telegram_id: int) -> tuple:
    """Get user and their accounts/cards for AI context."""
    result = await db.execute(
        select(User)
        .where(User.telegram_id == telegram_id)
        .options(selectinload(User.accounts).selectinload(Account.cards))
    )
    user = result.scalar_one_or_none()
    if not user:
        return None, []

    accounts_context = []
    for acc in user.accounts:
        accounts_context.append({
            "id": str(acc.id),
            "name": acc.name,
            "institution": acc.institution,
            "type": acc.account_type,
            "last_four": acc.last_four,
        })
        for card in acc.cards:
            accounts_context.append({
                "id": str(card.id),
                "name": card.name,
                "institution": card.institution,
                "type": f"{card.card_type} card",
                "last_four": card.last_four,
            })

    # Also get standalone credit cards
    card_result = await db.execute(
        select(Card).where(Card.user_id == user.id, Card.account_id.is_(None))
    )
    for card in card_result.scalars().all():
        accounts_context.append({
            "id": str(card.id),
            "name": card.name,
            "institution": card.institution,
            "type": f"{card.card_type} card",
            "last_four": card.last_four,
        })

    return user, accounts_context


def _format_parsed_expense(parsed: dict) -> str:
    """Format parsed expense data for display."""
    amount = parsed.get("total") or parsed.get("amount", 0)
    currency = parsed.get("currency", "UYU")
    description = parsed.get("description", "")
    merchant = parsed.get("merchant", "")
    category = parsed.get("category", "Other")
    expense_date = parsed.get("expense_date", date.today().isoformat())
    account_hint = parsed.get("account_hint") or parsed.get("payment_method") or ""
    confidence = parsed.get("confidence", 0)

    lines = [
        f"\U0001f4b0 *Amount:* {currency} {amount:,.2f}" if isinstance(amount, (int, float)) else f"\U0001f4b0 *Amount:* {currency} {amount}",
        f"\U0001f4dd *Description:* {description}" if description else None,
        f"\U0001f3ea *Merchant:* {merchant}" if merchant else None,
        f"\U0001f4c1 *Category:* {category}",
        f"\U0001f4c5 *Date:* {expense_date}",
        f"\U0001f4b3 *Payment:* {account_hint}" if account_hint else None,
    ]

    # Splits
    splits = parsed.get("split_with", [])
    if splits:
        split_lines = [f"  \u2022 {s['person_name']}: {currency} {s['amount']:,.2f}" for s in splits]
        lines.append("\U0001f91d *Split with:*\n" + "\n".join(split_lines))

    # Receipt items
    items = parsed.get("items", [])
    if items:
        item_lines = [f"  \u2022 {i['description']}: {currency} {i['amount']:,.2f}" for i in items[:8]]
        if len(items) > 8:
            item_lines.append(f"  _... and {len(items) - 8} more items_")
        lines.append("\U0001f9fe *Items:*\n" + "\n".join(item_lines))

    if confidence and confidence < 0.7:
        lines.append(f"\n\u26a0\ufe0f _Low confidence ({confidence:.0%}) - please review carefully_")

    return "\n".join(line for line in lines if line)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages as expense descriptions."""
    text = update.message.text
    if not text or text.startswith("/"):
        return

    tg_user = update.effective_user
    await update.message.reply_text("\U0001f914 Parsing your expense...")

    async with async_session() as db:
        user, accounts_context = await _get_user_context(db, tg_user.id)
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        try:
            parsed = await ai_service.parse_expense_text(text, accounts_context)
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            await update.message.reply_text("\u274c Sorry, I couldn't parse that. Please try again.")
            return

        if "error" in parsed:
            await update.message.reply_text(f"\u274c {parsed['error']}")
            return

        # Store parsed data in user_data for confirmation
        context.user_data["pending_expense"] = parsed
        context.user_data["input_method"] = "text"
        context.user_data["raw_input"] = text

        await update.message.reply_text(
            _format_parsed_expense(parsed),
            reply_markup=confirm_expense_keyboard(parsed),
            parse_mode="Markdown",
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle receipt photo uploads."""
    tg_user = update.effective_user
    photo = update.message.photo[-1]  # highest resolution

    await update.message.reply_text("\U0001f4f8 Analyzing your receipt...")

    # Download the photo
    file = await context.bot.get_file(photo.file_id)
    image_data = await file.download_as_bytearray()

    async with async_session() as db:
        user, accounts_context = await _get_user_context(db, tg_user.id)
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        try:
            parsed = await ai_service.parse_receipt_image(bytes(image_data), "image/jpeg", accounts_context)
        except Exception as e:
            logger.error(f"Receipt parsing error: {e}")
            await update.message.reply_text("\u274c Sorry, I couldn't read that receipt. Try a clearer photo.")
            return

        if "error" in parsed:
            await update.message.reply_text(f"\u274c {parsed['error']}")
            return

        context.user_data["pending_expense"] = parsed
        context.user_data["input_method"] = "receipt"
        context.user_data["raw_input"] = f"receipt_photo:{photo.file_id}"

        await update.message.reply_text(
            _format_parsed_expense(parsed),
            reply_markup=confirm_expense_keyboard(parsed),
            parse_mode="Markdown",
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages - transcribe then parse as text."""
    tg_user = update.effective_user
    voice = update.message.voice

    await update.message.reply_text("\U0001f3a4 Transcribing your voice message...")

    # Download voice
    file = await context.bot.get_file(voice.file_id)
    audio_data = await file.download_as_bytearray()

    try:
        transcription = await audio_service.transcribe_voice(bytes(audio_data), "ogg")
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        await update.message.reply_text("\u274c Sorry, I couldn't transcribe that audio. Please try again or send text.")
        return

    await update.message.reply_text(f'\U0001f4dd Transcribed: _"{transcription}"_\n\n\U0001f914 Parsing expense...', parse_mode="Markdown")

    async with async_session() as db:
        user, accounts_context = await _get_user_context(db, tg_user.id)
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        try:
            parsed = await ai_service.parse_expense_text(transcription, accounts_context)
        except Exception as e:
            logger.error(f"AI parsing error: {e}")
            await update.message.reply_text("\u274c Sorry, I couldn't parse that. Please try again.")
            return

        if "error" in parsed:
            await update.message.reply_text(f"\u274c {parsed['error']}")
            return

        context.user_data["pending_expense"] = parsed
        context.user_data["input_method"] = "audio"
        context.user_data["raw_input"] = transcription

        await update.message.reply_text(
            _format_parsed_expense(parsed),
            reply_markup=confirm_expense_keyboard(parsed),
            parse_mode="Markdown",
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button presses for expense confirmation flow."""
    query = update.callback_query
    await query.answer()

    data = query.data
    tg_user = update.effective_user

    if data == "expense:confirm":
        pending = context.user_data.get("pending_expense")
        if not pending:
            await query.edit_message_text("\u274c No pending expense to confirm.")
            return

        async with async_session() as db:
            user_result = await db.execute(
                select(User).where(User.telegram_id == tg_user.id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                await query.edit_message_text("\u274c User not found. Use /start first.")
                return

            expense = await expense_service.create_from_ai_result(
                db=db,
                user_id=user.id,
                parsed=pending,
                input_method=context.user_data.get("input_method", "text"),
                raw_input=context.user_data.get("raw_input"),
            )

            amount = pending.get("total") or pending.get("amount", 0)
            currency = pending.get("currency", "UYU")
            category = pending.get("category", "Other")
            merchant = pending.get("merchant", "")

            msg = f"\u2705 *Recorded!*\n{currency} {amount:,.2f}" if isinstance(amount, (int, float)) else f"\u2705 *Recorded!*\n{currency} {amount}"
            if merchant:
                msg += f" at {merchant}"
            msg += f" ({category})"

            # Check budget alerts
            alert = await budget_service.check_budget_alert(
                db, user.id, expense.category_id, expense.currency, expense.amount
            )
            if alert:
                msg += f"\n\n{alert}"

            await query.edit_message_text(msg, parse_mode="Markdown")
            context.user_data.pop("pending_expense", None)

    elif data == "expense:cancel":
        context.user_data.pop("pending_expense", None)
        await query.edit_message_text("\u274c Expense cancelled.")

    elif data == "expense:edit_category":
        await query.edit_message_text(
            "Select a category:",
            reply_markup=category_keyboard(),
        )

    elif data.startswith("cat:"):
        category_name = data[4:]
        pending = context.user_data.get("pending_expense")
        if pending:
            pending["category"] = category_name
            await query.edit_message_text(
                _format_parsed_expense(pending),
                reply_markup=confirm_expense_keyboard(pending),
                parse_mode="Markdown",
            )

    elif data == "expense:edit_account":
        async with async_session() as db:
            user, accounts_context = await _get_user_context(db, tg_user.id)
            if accounts_context:
                await query.edit_message_text(
                    "Select account/card:",
                    reply_markup=account_keyboard(accounts_context),
                )
            else:
                await query.edit_message_text(
                    "No accounts configured. Use /addaccount first.",
                )

    elif data.startswith("acc:"):
        acc_id = data[4:]
        pending = context.user_data.get("pending_expense")
        if pending:
            pending["account_hint"] = acc_id  # store the ID directly
            await query.edit_message_text(
                _format_parsed_expense(pending),
                reply_markup=confirm_expense_keyboard(pending),
                parse_mode="Markdown",
            )

    elif data == "expense:edit_amount":
        context.user_data["awaiting_amount_edit"] = True
        await query.edit_message_text(
            "Send me the correct amount (e.g. `1500` or `USD 50`):",
            parse_mode="Markdown",
        )

    elif data == "expense:back":
        pending = context.user_data.get("pending_expense")
        if pending:
            await query.edit_message_text(
                _format_parsed_expense(pending),
                reply_markup=confirm_expense_keyboard(pending),
                parse_mode="Markdown",
            )


async def handle_amount_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle amount edit when user is in amount-edit mode."""
    if not context.user_data.get("awaiting_amount_edit"):
        return

    text = update.message.text.strip()
    pending = context.user_data.get("pending_expense")
    if not pending:
        await update.message.reply_text("\u274c No pending expense.")
        return

    # Parse amount - check for currency prefix
    currency = pending.get("currency", "UYU")
    amount_str = text

    for prefix, cur in [("USD", "USD"), ("U$S", "USD"), ("US$", "USD"), ("UYU", "UYU")]:
        if text.upper().startswith(prefix):
            currency = cur
            amount_str = text[len(prefix):].strip()
            break

    try:
        amount = float(amount_str.replace(",", ""))
    except ValueError:
        await update.message.reply_text("\u274c Invalid amount. Send a number like `1500` or `USD 50`.", parse_mode="Markdown")
        return

    if "total" in pending:
        pending["total"] = amount
    else:
        pending["amount"] = amount
    pending["currency"] = currency
    context.user_data["awaiting_amount_edit"] = False

    await update.message.reply_text(
        _format_parsed_expense(pending),
        reply_markup=confirm_expense_keyboard(pending),
        parse_mode="Markdown",
    )
