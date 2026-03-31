"""Handlers for split/debt management commands."""

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services import split_service


async def debts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /debts - show who owes the user money."""
    tg_user = update.effective_user

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        balances = await split_service.get_unsettled_balances(db, user.id)

        if not balances:
            await update.message.reply_text("No one owes you anything! \U0001f389")
            return

        lines = ["\U0001f91d *Outstanding Debts*\n"]
        total = sum(balances.values())
        for person, amount in sorted(balances.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"\u2022 *{person}*: ${amount:,.2f}")

        lines.append(f"\n\U0001f4b0 *Total owed:* ${total:,.2f}")
        lines.append("\nUse `/settle <name>` to mark as paid back.")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def settle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settle <name> - mark someone's debts as settled."""
    tg_user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: `/settle <name>`\n"
            "Example: `/settle Juan`",
            parse_mode="Markdown",
        )
        return

    person_name = " ".join(args)

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        count = await split_service.settle_person(db, user.id, person_name)

        if count == 0:
            await update.message.reply_text(f"No unsettled debts found for \"{person_name}\".")
        else:
            await update.message.reply_text(
                f"\u2705 Settled {count} debt(s) for *{person_name}*!",
                parse_mode="Markdown",
            )
