"""Handler for /help command."""

from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = """*Available Commands* \U0001f4cb

*Recording Expenses:*
\U0001f4ac Send a text message \u2013 describe your expense naturally
\U0001f4f7 Send a receipt photo \u2013 I'll extract all the details
\U0001f3a4 Send a voice message \u2013 I'll transcribe and parse it

*Accounts & Cards:*
/accounts \u2013 List your bank accounts and cards
/addaccount \u2013 Add a bank account
/addcard \u2013 Add a debit or credit card

*Viewing Expenses:*
/recent \u2013 Show last 10 expenses
/summary \u2013 Monthly spending summary by category

*Splits & Debts:*
/debts \u2013 See who owes you money
/settle \u2013 Mark someone's debt as settled

*Budgets:*
/setbudget \u2013 Set a monthly budget for a category
/budget \u2013 View budget progress

*Bank Statements:*
\U0001f4ce Send a CSV file \u2013 I'll reconcile it against your expenses

*Tips:*
\u2022 Mention your card/account and I'll match it automatically
\u2022 Say "split with Juan" and I'll track who owes you
\u2022 I understand Spanish and English
\u2022 "$" = UYU, "U$S" = USD"""


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help - show all available commands."""
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")
