"""Handlers for /recent and /summary commands."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services import expense_service


async def recent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /recent - show last 10 expenses."""
    tg_user = update.effective_user

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        expenses = await expense_service.get_recent(db, user.id, limit=10)

        if not expenses:
            await update.message.reply_text("No expenses recorded yet. Send me a message to record one!")
            return

        lines = ["\U0001f4cb *Recent Expenses*\n"]
        for exp in expenses:
            cat_icon = exp.category.icon if exp.category else ""
            cat_name = exp.category.name if exp.category else "Uncategorized"
            merchant = f" at {exp.merchant}" if exp.merchant else ""
            lines.append(
                f"{cat_icon} {exp.expense_date.strftime('%d/%m')} \u2022 "
                f"*{exp.currency} {exp.amount:,.2f}*{merchant}\n"
                f"   _{exp.description}_"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summary - monthly spending summary by category."""
    tg_user = update.effective_user
    today = date.today()

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        summary = await expense_service.get_monthly_summary(db, user.id, today.year, today.month)

        if not summary:
            await update.message.reply_text(f"No expenses for {today.strftime('%B %Y')} yet.")
            return

        # Group by currency
        by_currency: dict[str, list] = {}
        for item in summary:
            by_currency.setdefault(item["currency"], []).append(item)

        lines = [f"\U0001f4ca *Spending Summary \u2022 {today.strftime('%B %Y')}*\n"]

        for currency, items in by_currency.items():
            total = sum(item["total"] for item in items)
            lines.append(f"\n\U0001f4b0 *{currency}* \u2022 Total: *{total:,.2f}*\n")

            for item in items:
                pct = (item["total"] / total * 100) if total > 0 else 0
                bar = _progress_bar(pct / 100, 10)
                lines.append(
                    f"{item['icon']} {item['category']}\n"
                    f"   {bar} {item['total']:,.2f} ({item['count']}x) \u2022 {pct:.0f}%"
                )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _progress_bar(fraction: float, width: int = 10) -> str:
    """Create a Unicode progress bar."""
    filled = int(fraction * width)
    return "\u2588" * filled + "\u2591" * (width - filled)
