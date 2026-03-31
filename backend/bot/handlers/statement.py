"""Handler for bank statement CSV upload and reconciliation."""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database import async_session
from app.models.user import User
from app.models.account import Account
from app.services import reconciliation_service


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads - process CSV bank statements."""
    document = update.message.document
    if not document:
        return

    # Only handle CSV files
    file_name = document.file_name or ""
    if not file_name.lower().endswith(".csv"):
        await update.message.reply_text(
            "I currently support CSV bank statements.\n"
            "Please upload a `.csv` file.",
            parse_mode="Markdown",
        )
        return

    tg_user = update.effective_user

    async with async_session() as db:
        user_result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text("Please use /start first!")
            return

        # Get user's default account (or first account)
        acc_result = await db.execute(
            select(Account)
            .where(Account.user_id == user.id)
            .order_by(Account.is_default.desc())
        )
        account = acc_result.scalars().first()
        if not account:
            await update.message.reply_text(
                "You need to add a bank account first.\n"
                "Use `/addaccount` to set one up.",
                parse_mode="Markdown",
            )
            return

        await update.message.reply_text("\U0001f4ca Processing your bank statement...")

        # Download and read the CSV
        file = await context.bot.get_file(document.file_id)
        file_bytes = await file.download_as_bytearray()

        try:
            csv_data = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                csv_data = file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                await update.message.reply_text("\u274c Could not read the file. Please check the encoding.")
                return

        today = date.today()
        try:
            result = await reconciliation_service.process_csv_statement(
                db=db,
                user_id=user.id,
                account_id=account.id,
                csv_data=csv_data,
                statement_month=today.replace(day=1),
                file_url=f"telegram:{document.file_id}",
            )
        except Exception as e:
            await update.message.reply_text(f"\u274c Error processing statement: {e}")
            return

        total = result["total_transactions"]
        matched = result["matched"]
        unmatched = result["unmatched"]

        match_pct = (matched / total * 100) if total > 0 else 0

        await update.message.reply_text(
            f"\u2705 *Statement Processed*\n\n"
            f"\U0001f4c4 *Total transactions:* {total}\n"
            f"\u2705 *Matched:* {matched} ({match_pct:.0f}%)\n"
            f"\u2753 *Unmatched:* {unmatched}\n\n"
            f"_Matched against account: {account.name} ({account.institution})_",
            parse_mode="Markdown",
        )
