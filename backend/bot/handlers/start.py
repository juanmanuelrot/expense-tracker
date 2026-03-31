"""Handler for /start command - user onboarding."""

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database import async_session
from app.models.user import User


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start - create user if new, welcome them."""
    tg_user = update.effective_user
    if not tg_user:
        return

    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
            )
            db.add(user)
            await db.commit()
            await update.message.reply_text(
                f"Welcome {tg_user.first_name}! \U0001f44b\n\n"
                "I'm your AI expense tracker. Here's how to use me:\n\n"
                "\U0001f4ac *Send a text message* describing your expense\n"
                '   _"Gasté $500 en el super con la débito del BROU"_\n\n'
                "\U0001f4f7 *Send a photo* of a receipt\n\n"
                "\U0001f3a4 *Send a voice message* describing your expense\n\n"
                "I'll parse it, categorize it, and ask you to confirm.\n\n"
                "Use /help to see all commands.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"Welcome back {tg_user.first_name}! \U0001f44b\n"
                "Send me a text, photo, or voice message to record an expense.\n"
                "Use /help to see all commands.",
                parse_mode="Markdown",
            )
