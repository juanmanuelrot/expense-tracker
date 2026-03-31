"""Inline keyboard builders for the Telegram bot."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_expense_keyboard(expense_data: dict) -> InlineKeyboardMarkup:
    """Keyboard shown after AI parses an expense, for user to confirm/edit/cancel."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("\u2705 Confirm", callback_data="expense:confirm"),
            InlineKeyboardButton("\u274c Cancel", callback_data="expense:cancel"),
        ],
        [
            InlineKeyboardButton("\u270f\ufe0f Edit Amount", callback_data="expense:edit_amount"),
            InlineKeyboardButton("\U0001f4c1 Edit Category", callback_data="expense:edit_category"),
        ],
        [
            InlineKeyboardButton("\U0001f4b3 Edit Account", callback_data="expense:edit_account"),
        ],
    ])


def category_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting a category."""
    categories = [
        ("\U0001f354 Food & Dining", "cat:Food & Dining"),
        ("\U0001f6d2 Groceries", "cat:Groceries"),
        ("\U0001f68c Transport", "cat:Transport"),
        ("\U0001f3ac Entertainment", "cat:Entertainment"),
        ("\U0001f6cd\ufe0f Shopping", "cat:Shopping"),
        ("\U0001f4a1 Bills", "cat:Bills & Utilities"),
        ("\U0001f3e5 Health", "cat:Health"),
        ("\u2708\ufe0f Travel", "cat:Travel"),
        ("\U0001f4da Education", "cat:Education"),
        ("\U0001f3e0 Home", "cat:Home"),
        ("\U0001f487 Personal", "cat:Personal Care"),
        ("\U0001f4f1 Subscriptions", "cat:Subscriptions"),
        ("\U0001f4cb Other", "cat:Other"),
    ]
    rows = [
        [InlineKeyboardButton(label, callback_data=data)]
        for label, data in categories
    ]
    rows.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="expense:back")])
    return InlineKeyboardMarkup(rows)


def account_keyboard(accounts: list[dict]) -> InlineKeyboardMarkup:
    """Keyboard for selecting an account/card."""
    rows = []
    for acc in accounts:
        label = f"{acc['name']}"
        if acc.get("last_four"):
            label += f" (*{acc['last_four']})"
        rows.append([InlineKeyboardButton(label, callback_data=f"acc:{acc['id']}")])
    rows.append([InlineKeyboardButton("\u2b05\ufe0f Back", callback_data="expense:back")])
    return InlineKeyboardMarkup(rows)
