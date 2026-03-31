import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.card import Card
    from app.models.category import Category
    from app.models.user import User


class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"))
    card_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cards.id"))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="UYU")
    description: Mapped[str] = mapped_column(Text)
    merchant: Mapped[str | None] = mapped_column(String(200))
    expense_date: Mapped[date] = mapped_column(Date)

    input_method: Mapped[str] = mapped_column(String(20))  # text, receipt, audio, statement_import
    raw_input: Mapped[str | None] = mapped_column(Text)
    receipt_image_url: Mapped[str | None] = mapped_column(String(500))
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="expenses")
    account: Mapped["Account | None"] = relationship()
    card: Mapped["Card | None"] = relationship()
    category: Mapped["Category | None"] = relationship()
    items: Mapped[list["ExpenseItem"]] = relationship(back_populates="expense", cascade="all, delete-orphan")
    splits: Mapped[list["Split"]] = relationship(back_populates="expense", cascade="all, delete-orphan")


class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id"))
    description: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    expense: Mapped["Expense"] = relationship(back_populates="items")


class Split(Base, TimestampMixin):
    __tablename__ = "splits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id"))
    person_name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_settled: Mapped[bool] = mapped_column(Boolean, default=False)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    expense: Mapped["Expense"] = relationship(back_populates="splits")
