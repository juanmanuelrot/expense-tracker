"""Handlers for budget management commands."""

from decimal import Decimal

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.services import budget_service


async def setbudget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /setbudget <category> <amount> [currency] [period].

    Examples:
        /setbudget Food 15000
        /setbudget Transport 5000 UYU monthly
        /setbudget Shopping 200 USD monthly
    """
    tg_user = update.effective_user
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "*Set a Budget*\n\n"
            "Usage: `/setbudget <category> <amount> [currency] [period]`\n\n"
            "Defaults: currency=UYU, period=monthly\n\n"
            "Examples:\n"
            "`/setbudget Food 15000`\n"
            "`/setbudget Transport 5000 UYU monthly`\n"
            "`/setbudget Shopping 200 USD monthly`\n\n"
            "Categories: Food & Dining, Groceries, Transport, Entertainment, "
            "Shopping, Bills & Utilities, Health, Travel, Education, Home, "
            "Personal Care, Subscriptions",
            parse_mode="Markdown",
        )
        return

    category_name = args[0]
    try:
        amount = Decimal(args[1].replace(",", ""))
    except Exception:
        await update.message.reply_text("\u274c Invalid amount.")
        return

    currency = args[2].upper() if len(args) > 2 and args[2].upper() in ("UYU", "USD") else "UYU"
    period = args[3].lower() if len(args) > 3 else "monthly"

    if period not in ("weekly", "monthly", "yearly"):
        period = "monthly"

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        budget = await budget_service.create_budget(
            db, user.id, category_name, amount, currency, period
        )

        await update.message.reply_text(
            f"\u2705 Budget set: *{category_name}* \u2022 {currency} {amount:,.0f} / {period}",
            parse_mode="Markdown",
        )


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /budget - show all budgets with progress."""
    tg_user = update.effective_user

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        budgets = await budget_service.get_budgets_with_spending(db, user.id)

        if not budgets:
            await update.message.reply_text(
                "No budgets set. Use `/setbudget` to create one.",
                parse_mode="Markdown",
            )
            return

        lines = ["\U0001f4ca *Budget Progress*\n"]

        for b in budgets:
            pct = b["percentage"]
            bar = _budget_bar(pct / 100, 15)

            if pct >= 100:
                status = "\U0001f534"
            elif pct >= 80:
                status = "\U0001f7e1"
            else:
                status = "\U0001f7e2"

            lines.append(
                f"{b['icon']} *{b['category']}* ({b['period']})\n"
                f"   {bar}\n"
                f"   {status} {b['currency']} {b['spent']:,.0f} / {b['budget']:,.0f} ({pct:.0f}%)"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


def _budget_bar(fraction: float, width: int = 15) -> str:
    """Create a budget progress bar with color indicators."""
    fraction = min(fraction, 1.0)
    filled = int(fraction * width)
    return "\u2588" * filled + "\u2591" * (width - filled)
