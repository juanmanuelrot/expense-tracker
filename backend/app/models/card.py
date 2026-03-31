import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.user import User


class Card(Base, TimestampMixin):
    """Debit or credit card. Debit cards link to a bank account; credit cards stand alone."""

    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("accounts.id"))  # required for debit, null for credit
    name: Mapped[str] = mapped_column(String(100))  # e.g. "BROU Visa Débito"
    card_type: Mapped[str] = mapped_column(String(10))  # debit, credit
    institution: Mapped[str] = mapped_column(String(100))  # e.g. "BROU", "OCA"
    last_four: Mapped[str | None] = mapped_column(String(4))
    currencies: Mapped[list] = mapped_column(JSON, default=lambda: ["UYU", "USD"])

    user: Mapped["User"] = relationship(back_populates="cards")
    account: Mapped["Account | None"] = relationship(back_populates="cards")
