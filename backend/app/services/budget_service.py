"""Budget management and spending alerts."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.expense import Expense
from app.models.category import Category


async def get_budgets_with_spending(
    db: AsyncSession, user_id: uuid.UUID
) -> list[dict]:
    """Get all active budgets with current period spending."""
    result = await db.execute(
        select(Budget)
        .options()
        .where(Budget.user_id == user_id, Budget.is_active.is_(True))
    )
    budgets = list(result.scalars().all())

    today = date.today()
    output = []

    for budget in budgets:
        # Calculate current period spending
        spent = await _get_period_spending(db, user_id, budget, today)

        # Get category name
        cat_name = "Overall"
        cat_icon = ""
        if budget.category_id:
            cat_result = await db.execute(
                select(Category).where(Category.id == budget.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if cat:
                cat_name = cat.name
                cat_icon = cat.icon

        budget_amount = float(budget.amount)
        spent_float = float(spent)
        pct = (spent_float / budget_amount * 100) if budget_amount > 0 else 0

        output.append({
            "id": budget.id,
            "category": cat_name,
            "icon": cat_icon,
            "budget": budget_amount,
            "spent": spent_float,
            "currency": budget.currency,
            "period": budget.period,
            "percentage": round(pct, 1),
        })

    return output


async def check_budget_alert(
    db: AsyncSession, user_id: uuid.UUID, category_id: uuid.UUID | None, currency: str, amount: Decimal
) -> str | None:
    """Check if recording this expense triggers a budget alert. Returns alert message or None."""
    if not category_id:
        return None

    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.currency == currency,
            Budget.is_active.is_(True),
        )
    )
    budget = result.scalar_one_or_none()
    if not budget:
        return None

    today = date.today()
    spent = await _get_period_spending(db, user_id, budget, today)
    new_total = spent + amount
    pct = float(new_total) / float(budget.amount) * 100 if budget.amount > 0 else 0

    # Get category name
    cat_result = await db.execute(select(Category).where(Category.id == category_id))
    cat = cat_result.scalar_one_or_none()
    cat_name = cat.name if cat else "this category"

    if pct >= 100:
        return f"\u26a0\ufe0f Budget exceeded for {cat_name}! {new_total:.0f}/{budget.amount:.0f} {currency} ({pct:.0f}%)"
    elif pct >= 80:
        return f"\u26a0\ufe0f Approaching budget limit for {cat_name}: {new_total:.0f}/{budget.amount:.0f} {currency} ({pct:.0f}%)"

    return None


async def create_budget(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_name: str,
    amount: Decimal,
    currency: str,
    period: str = "monthly",
) -> Budget:
    """Create a new budget for a category."""
    # Find category
    result = await db.execute(
        select(Category).where(
            Category.name.ilike(f"%{category_name}%"),
            (Category.user_id == user_id) | (Category.user_id.is_(None)),
        )
    )
    cat = result.scalar_one_or_none()

    budget = Budget(
        user_id=user_id,
        category_id=cat.id if cat else None,
        amount=amount,
        currency=currency,
        period=period,
        start_date=date.today().replace(day=1),
    )
    db.add(budget)
    await db.commit()
    await db.refresh(budget)
    return budget


async def _get_period_spending(
    db: AsyncSession, user_id: uuid.UUID, budget: Budget, today: date
) -> Decimal:
    """Calculate spending in the current budget period."""
    if budget.period == "monthly":
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)
    elif budget.period == "weekly":
        start = today - __import__("datetime").timedelta(days=today.weekday())
        end = start + __import__("datetime").timedelta(days=7)
    else:  # yearly
        start = today.replace(month=1, day=1)
        end = today.replace(year=today.year + 1, month=1, day=1)

    query = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.user_id == user_id,
        Expense.currency == budget.currency,
        Expense.expense_date >= start,
        Expense.expense_date < end,
    )
    if budget.category_id:
        query = query.where(Expense.category_id == budget.category_id)

    result = await db.execute(query)
    return result.scalar()
