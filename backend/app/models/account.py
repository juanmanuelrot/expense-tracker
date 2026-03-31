import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.user import User


class Account(Base, TimestampMixin):
    """Bank account (e.g. BROU checking, Itaú savings). Multi-currency: a single account can hold UYU and USD."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))  # e.g. "BROU Checking"
    institution: Mapped[str] = mapped_column(String(100))  # e.g. "BROU"
    account_type: Mapped[str] = mapped_column(String(20))  # checking, savings, cash
    last_four: Mapped[str | None] = mapped_column(String(4))
    currencies: Mapped[list] = mapped_column(JSON, default=lambda: ["UYU", "USD"])
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="accounts")
    cards: Mapped[list["Card"]] = relationship(back_populates="account", cascade="all, delete-orphan")
