"""Telegram bot entry point. Registers all handlers and starts polling."""

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config import settings
from bot.handlers.start import start_command
from bot.handlers.help import help_command
from bot.handlers.expense import (
    handle_text,
    handle_photo,
    handle_voice,
    handle_callback,
    handle_amount_edit,
)
from bot.handlers.accounts import list_accounts, add_account, add_card
from bot.handlers.report import recent_command, summary_command
from bot.handlers.splits import debts_command, settle_command
from bot.handlers.budget import setbudget_command, budget_command
from bot.handlers.statement import handle_document

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set. Please configure it in .env")
        return

    app = Application.builder().token(settings.telegram_bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("accounts", list_accounts))
    app.add_handler(CommandHandler("addaccount", add_account))
    app.add_handler(CommandHandler("addcard", add_card))
    app.add_handler(CommandHandler("recent", recent_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("debts", debts_command))
    app.add_handler(CommandHandler("settle", settle_command))
    app.add_handler(CommandHandler("setbudget", setbudget_command))
    app.add_handler(CommandHandler("budget", budget_command))

    # Callback query handler (inline keyboard buttons)
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Message handlers (order matters - more specific first)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
