"""Expense CRUD and creation from AI-parsed results."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expense import Expense, ExpenseItem, Split
from app.models.category import Category
from app.models.account import Account
from app.models.card import Card


async def create_from_ai_result(
    db: AsyncSession,
    user_id: uuid.UUID,
    parsed: dict[str, Any],
    input_method: str,
    raw_input: str | None = None,
    receipt_image_url: str | None = None,
) -> Expense:
    """Create an expense from AI-parsed data."""
    # Resolve category
    category_id = await _resolve_category(db, user_id, parsed.get("category", "Other"))

    # Resolve account/card from hint
    account_id, card_id = await _resolve_account(db, user_id, parsed.get("account_hint") or parsed.get("payment_method"))

    # Handle receipt vs text format
    amount = Decimal(str(parsed.get("total") or parsed.get("amount", 0)))
    description = parsed.get("description", parsed.get("merchant", ""))
    merchant = parsed.get("merchant")
    expense_date_str = parsed.get("expense_date", date.today().isoformat())

    try:
        expense_date = date.fromisoformat(expense_date_str)
    except (ValueError, TypeError):
        expense_date = date.today()

    expense = Expense(
        user_id=user_id,
        account_id=account_id,
        card_id=card_id,
        category_id=category_id,
        amount=amount,
        currency=parsed.get("currency", "UYU"),
        description=description,
        merchant=merchant,
        expense_date=expense_date,
        input_method=input_method,
        raw_input=raw_input,
        receipt_image_url=receipt_image_url,
        ai_confidence=parsed.get("confidence"),
    )
    db.add(expense)

    # Add line items if present (from receipt parsing)
    for item_data in parsed.get("items", []):
        item = ExpenseItem(
            expense_id=expense.id,
            description=item_data["description"],
            quantity=Decimal(str(item_data.get("quantity", 1))) if item_data.get("quantity") else None,
            unit_price=Decimal(str(item_data["unit_price"])) if item_data.get("unit_price") else None,
            amount=Decimal(str(item_data["amount"])),
        )
        expense.items.append(item)

    # Add splits if present
    for split_data in parsed.get("split_with", []):
        split = Split(
            expense_id=expense.id,
            person_name=split_data["person_name"],
            amount=Decimal(str(split_data["amount"])),
        )
        expense.splits.append(split)

    await db.commit()
    await db.refresh(expense)
    return expense


async def get_recent(db: AsyncSession, user_id: uuid.UUID, limit: int = 10) -> list[Expense]:
    """Get the most recent expenses for a user."""
    result = await db.execute(
        select(Expense)
        .where(Expense.user_id == user_id)
        .options(selectinload(Expense.category), selectinload(Expense.account), selectinload(Expense.card))
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_monthly_summary(
    db: AsyncSession, user_id: uuid.UUID, year: int, month: int
) -> list[dict]:
    """Get spending totals grouped by category for a given month."""
    result = await db.execute(
        select(
            Category.name,
            Category.icon,
            Expense.currency,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .join(Category, Expense.category_id == Category.id, isouter=True)
        .where(
            Expense.user_id == user_id,
            extract("year", Expense.expense_date) == year,
            extract("month", Expense.expense_date) == month,
        )
        .group_by(Category.name, Category.icon, Expense.currency)
        .order_by(func.sum(Expense.amount).desc())
    )
    rows = result.all()
    return [
        {
            "category": row.name or "Uncategorized",
            "icon": row.icon or "",
            "currency": row.currency,
            "total": float(row.total),
            "count": row.count,
        }
        for row in rows
    ]


async def delete_expense(db: AsyncSession, expense_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Delete an expense by ID if it belongs to the user."""
    result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
    )
    expense = result.scalar_one_or_none()
    if not expense:
        return False
    await db.delete(expense)
    await db.commit()
    return True


async def _resolve_category(db: AsyncSession, user_id: uuid.UUID, category_name: str) -> uuid.UUID | None:
    """Find category by name (system defaults or user-specific)."""
    result = await db.execute(
        select(Category).where(
            Category.name == category_name,
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
            Category.is_active.is_(True),
        )
    )
    cat = result.scalar_one_or_none()
    return cat.id if cat else None


async def _resolve_account(
    db: AsyncSession, user_id: uuid.UUID, hint: str | None
) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Fuzzy-match an account or card from a text hint. Returns (account_id, card_id)."""
    if not hint:
        return None, None

    hint_lower = hint.lower()

    # Check if it's cash
    if any(w in hint_lower for w in ["efectivo", "cash"]):
        # Look for a cash account
        result = await db.execute(
            select(Account).where(Account.user_id == user_id, Account.account_type == "cash")
        )
        acc = result.scalar_one_or_none()
        return (acc.id if acc else None), None

    # Try to match a card first (more specific)
    result = await db.execute(select(Card).where(Card.user_id == user_id))
    cards = result.scalars().all()
    for card in cards:
        if _fuzzy_match(hint_lower, card.name.lower(), card.institution.lower(), card.last_four):
            return card.account_id, card.id

    # Try to match an account
    result = await db.execute(select(Account).where(Account.user_id == user_id))
    accounts = result.scalars().all()
    for acc in accounts:
        if _fuzzy_match(hint_lower, acc.name.lower(), acc.institution.lower(), acc.last_four):
            return acc.id, None

    return None, None


def _fuzzy_match(hint: str, name: str, institution: str, last_four: str | None) -> bool:
    """Simple fuzzy matching for account/card identification."""
    # Check if institution name appears in hint
    if institution and institution in hint:
        return True
    # Check if card/account name appears in hint
    if name and any(word in hint for word in name.split() if len(word) > 2):
        return True
    # Check last four digits
    if last_four and last_four in hint:
        return True
    return False
