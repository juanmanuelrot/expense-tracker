"""Handlers for managing bank accounts and cards."""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.user import User
from app.models.account import Account
from app.models.card import Card


async def list_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /accounts - list all accounts and cards."""
    tg_user = update.effective_user

    async with async_session() as db:
        result = await db.execute(
            select(User)
            .where(User.telegram_id == tg_user.id)
            .options(
                selectinload(User.accounts).selectinload(Account.cards),
                selectinload(User.cards),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        if not user.accounts and not user.cards:
            await update.message.reply_text(
                "No accounts configured yet.\n\n"
                "Use /addaccount to add a bank account\n"
                "Use /addcard to add a debit or credit card"
            )
            return

        lines = ["\U0001f3e6 *Your Accounts & Cards*\n"]

        for acc in user.accounts:
            default = " \u2b50" if acc.is_default else ""
            currencies = ", ".join(acc.currencies) if acc.currencies else "UYU"
            lines.append(
                f"*{acc.name}*{default}\n"
                f"  {acc.institution} \u2022 {acc.account_type} \u2022 {currencies}"
            )
            if acc.last_four:
                lines[-1] += f" \u2022 *{acc.last_four}"

            # Show linked cards
            for card in acc.cards:
                card_last = f" (*{card.last_four})" if card.last_four else ""
                lines.append(f"  \U0001f4b3 {card.name}{card_last} ({card.card_type})")

        # Standalone credit cards
        standalone_cards = [c for c in user.cards if c.account_id is None]
        if standalone_cards:
            lines.append("\n\U0001f4b3 *Standalone Credit Cards*")
            for card in standalone_cards:
                card_last = f" (*{card.last_four})" if card.last_four else ""
                lines.append(f"  {card.name}{card_last} \u2022 {card.institution}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def add_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addaccount - add a new bank account.

    Usage: /addaccount <name> <institution> <type> [last4]
    Example: /addaccount "Caja de Ahorro" BROU checking 1234
    """
    tg_user = update.effective_user
    args = context.args

    if not args or len(args) < 3:
        await update.message.reply_text(
            "*Add a bank account*\n\n"
            "Usage: `/addaccount <name> <institution> <type> [last4]`\n\n"
            "Types: `checking`, `savings`, `cash`\n\n"
            "Examples:\n"
            '`/addaccount "Caja Ahorro" BROU checking`\n'
            '`/addaccount "Cuenta USD" Itaú savings 5678`\n'
            "`/addaccount Efectivo Cash cash`",
            parse_mode="Markdown",
        )
        return

    # Parse arguments - name can be quoted
    raw = " ".join(args)
    if raw.startswith('"'):
        end_quote = raw.find('"', 1)
        if end_quote > 0:
            name = raw[1:end_quote]
            rest = raw[end_quote + 1:].strip().split()
        else:
            name = args[0]
            rest = args[1:]
    else:
        name = args[0]
        rest = args[1:]

    if len(rest) < 2:
        await update.message.reply_text("\u274c Need at least: name, institution, and type.")
        return

    institution = rest[0]
    acc_type = rest[1].lower()
    last_four = rest[2] if len(rest) > 2 else None

    if acc_type not in ("checking", "savings", "cash"):
        await update.message.reply_text("\u274c Type must be: `checking`, `savings`, or `cash`", parse_mode="Markdown")
        return

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        # Check if this is the first account (make it default)
        count_result = await db.execute(select(Account).where(Account.user_id == user.id))
        is_first = not count_result.scalars().first()

        account = Account(
            user_id=user.id,
            name=name,
            institution=institution,
            account_type=acc_type,
            last_four=last_four,
            is_default=is_first,
        )
        db.add(account)
        await db.commit()

        default_text = " (set as default)" if is_first else ""
        await update.message.reply_text(
            f"\u2705 Account added: *{name}* at {institution}{default_text}",
            parse_mode="Markdown",
        )


async def add_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addcard - add a debit or credit card.

    Usage: /addcard <name> <institution> <debit|credit> [last4] [account_name]
    Example: /addcard "Visa Gold" OCA credit 4567
    Example: /addcard "BROU Débito" BROU debit 1234 "Caja de Ahorro"
    """
    tg_user = update.effective_user
    args = context.args

    if not args or len(args) < 3:
        await update.message.reply_text(
            "*Add a card*\n\n"
            "Usage: `/addcard <name> <institution> <debit|credit> [last4]`\n\n"
            "For debit cards, I'll ask which account to link.\n\n"
            "Examples:\n"
            '`/addcard "Visa Gold" OCA credit 4567`\n'
            '`/addcard "BROU Débito" BROU debit 1234`',
            parse_mode="Markdown",
        )
        return

    raw = " ".join(args)
    if raw.startswith('"'):
        end_quote = raw.find('"', 1)
        if end_quote > 0:
            name = raw[1:end_quote]
            rest = raw[end_quote + 1:].strip().split()
        else:
            name = args[0]
            rest = args[1:]
    else:
        name = args[0]
        rest = args[1:]

    if len(rest) < 2:
        await update.message.reply_text("\u274c Need at least: name, institution, and type (debit/credit).")
        return

    institution = rest[0]
    card_type = rest[1].lower()
    last_four = rest[2] if len(rest) > 2 else None

    if card_type not in ("debit", "credit"):
        await update.message.reply_text("\u274c Card type must be: `debit` or `credit`", parse_mode="Markdown")
        return

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        # For debit cards, try to auto-link to matching institution account
        account_id = None
        if card_type == "debit":
            acc_result = await db.execute(
                select(Account).where(
                    Account.user_id == user.id,
                    Account.institution.ilike(f"%{institution}%"),
                )
            )
            account = acc_result.scalar_one_or_none()
            if account:
                account_id = account.id

        card = Card(
            user_id=user.id,
            account_id=account_id,
            name=name,
            card_type=card_type,
            institution=institution,
            last_four=last_four,
        )
        db.add(card)
        await db.commit()

        linked_text = ""
        if account_id:
            await db.refresh(card)
            linked_text = f" (linked to {institution} account)"

        await update.message.reply_text(
            f"\u2705 Card added: *{name}* ({card_type}){linked_text}",
            parse_mode="Markdown",
        )
