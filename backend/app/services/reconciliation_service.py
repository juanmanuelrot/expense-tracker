"""Bank statement CSV reconciliation service."""

import csv
import io
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.expense import Expense
from app.models.statement import BankStatement, StatementTransaction


async def process_csv_statement(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    csv_data: str,
    statement_month: date,
    file_url: str,
) -> dict:
    """Process a CSV bank statement and match against recorded expenses."""
    # Create statement record
    statement = BankStatement(
        user_id=user_id,
        account_id=account_id,
        file_url=file_url,
        file_type="csv",
        statement_month=statement_month,
        status="processing",
    )
    db.add(statement)
    await db.flush()

    # Parse CSV - try to auto-detect columns
    transactions = _parse_csv(csv_data)

    matched = 0
    unmatched = 0

    for txn in transactions:
        stmt_txn = StatementTransaction(
            statement_id=statement.id,
            date=txn["date"],
            description=txn["description"],
            amount=txn["amount"],
            currency=txn.get("currency", "UYU"),
        )

        # Try to match against existing expenses
        match = await _find_matching_expense(
            db, user_id, account_id, txn["date"], txn["amount"]
        )
        if match:
            stmt_txn.matched_expense_id = match.id
            stmt_txn.match_status = "matched"
            match.is_reconciled = True
            matched += 1
        else:
            stmt_txn.match_status = "unmatched"
            unmatched += 1

        db.add(stmt_txn)

    statement.status = "completed"
    await db.commit()

    return {
        "statement_id": str(statement.id),
        "total_transactions": len(transactions),
        "matched": matched,
        "unmatched": unmatched,
    }


def _parse_csv(csv_data: str) -> list[dict]:
    """Parse CSV bank statement. Tries to auto-detect column layout."""
    reader = csv.DictReader(io.StringIO(csv_data))
    transactions = []

    # Common column name patterns
    date_cols = ["date", "fecha", "transaction date", "fecha operación", "fecha_operacion"]
    desc_cols = ["description", "descripción", "descripcion", "concepto", "detalle", "detail"]
    amount_cols = ["amount", "monto", "importe", "valor"]
    debit_cols = ["debit", "débito", "debito", "cargo"]
    credit_cols = ["credit", "crédito", "credito", "abono"]

    fieldnames = [f.lower().strip() for f in (reader.fieldnames or [])]

    def _find_col(candidates: list[str]) -> str | None:
        for c in candidates:
            for f in fieldnames:
                if c in f:
                    return reader.fieldnames[fieldnames.index(f)]
        return None

    date_col = _find_col(date_cols)
    desc_col = _find_col(desc_cols)
    amount_col = _find_col(amount_cols)
    debit_col = _find_col(debit_cols)
    credit_col = _find_col(credit_cols)

    for row in reader:
        try:
            # Parse date
            raw_date = row.get(date_col, "") if date_col else ""
            txn_date = _parse_date(raw_date)
            if not txn_date:
                continue

            # Parse description
            desc = row.get(desc_col, "") if desc_col else ""

            # Parse amount
            if amount_col:
                amount = _parse_amount(row.get(amount_col, "0"))
            elif debit_col and credit_col:
                debit = _parse_amount(row.get(debit_col, "0"))
                credit = _parse_amount(row.get(credit_col, "0"))
                amount = debit if debit > 0 else -credit
            else:
                continue

            if amount == 0:
                continue

            transactions.append({
                "date": txn_date,
                "description": desc.strip(),
                "amount": abs(amount),
            })
        except (ValueError, KeyError):
            continue

    return transactions


def _parse_date(raw: str) -> date | None:
    """Try multiple date formats."""
    raw = raw.strip()
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d.%m.%Y"]:
        try:
            return __import__("datetime").datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_amount(raw: str) -> Decimal:
    """Parse amount string, handling commas and dots."""
    raw = raw.strip().replace("$", "").replace(" ", "")
    if not raw:
        return Decimal("0")
    # Handle comma as decimal separator (e.g. "1.234,56")
    if "," in raw and "." in raw:
        if raw.rindex(",") > raw.rindex("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return abs(Decimal(raw))
    except Exception:
        return Decimal("0")


async def _find_matching_expense(
    db: AsyncSession,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    txn_date: date,
    amount: Decimal,
) -> Expense | None:
    """Find a matching expense by amount and date (within 2-day window)."""
    result = await db.execute(
        select(Expense).where(
            Expense.user_id == user_id,
            Expense.amount == amount,
            Expense.expense_date >= txn_date - timedelta(days=2),
            Expense.expense_date <= txn_date + timedelta(days=2),
            Expense.is_reconciled.is_(False),
        )
    )
    return result.scalar_one_or_none()
