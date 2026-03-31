"""Service for managing expense splits and debt tracking."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.expense import Split, Expense


async def get_unsettled_balances(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Decimal]:
    """Get total unsettled amount per person (who owes the user)."""
    result = await db.execute(
        select(Split.person_name, func.sum(Split.amount).label("total"))
        .join(Expense, Split.expense_id == Expense.id)
        .where(Expense.user_id == user_id, Split.is_settled.is_(False))
        .group_by(Split.person_name)
    )
    return {row.person_name: row.total for row in result.all()}


async def settle_person(db: AsyncSession, user_id: uuid.UUID, person_name: str) -> int:
    """Mark all debts from a person as settled. Returns count of settled splits."""
    result = await db.execute(
        select(Split)
        .join(Expense, Split.expense_id == Expense.id)
        .where(
            Expense.user_id == user_id,
            Split.person_name.ilike(f"%{person_name}%"),
            Split.is_settled.is_(False),
        )
    )
    splits = list(result.scalars().all())
    now = datetime.now(timezone.utc)
    for split in splits:
        split.is_settled = True
        split.settled_at = now
    await db.commit()
    return len(splits)


async def add_split(
    db: AsyncSession,
    expense_id: uuid.UUID,
    person_name: str,
    amount: Decimal,
) -> Split:
    """Add a split to an existing expense."""
    split = Split(
        expense_id=expense_id,
        person_name=person_name,
        amount=amount,
    )
    db.add(split)
    await db.commit()
    await db.refresh(split)
    return split
