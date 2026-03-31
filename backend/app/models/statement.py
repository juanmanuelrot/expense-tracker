import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class BankStatement(Base, TimestampMixin):
    __tablename__ = "bank_statements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id"))
    file_url: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))  # csv, pdf
    statement_month: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    transactions: Mapped[list["StatementTransaction"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class StatementTransaction(Base):
    __tablename__ = "statement_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    statement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bank_statements.id"))
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UYU")
    matched_expense_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("expenses.id"))
    match_status: Mapped[str] = mapped_column(String(20), default="unmatched")  # matched, unmatched, discrepancy

    statement: Mapped["BankStatement"] = relationship(back_populates="transactions")
