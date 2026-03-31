import uuid

from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))  # null = system default
    name: Mapped[str] = mapped_column(String(50))
    icon: Mapped[str] = mapped_column(String(10), default="")
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# Default system categories seeded on first migration
DEFAULT_CATEGORIES = [
    ("Food & Dining", "\U0001f354"),
    ("Groceries", "\U0001f6d2"),
    ("Transport", "\U0001f68c"),
    ("Entertainment", "\U0001f3ac"),
    ("Shopping", "\U0001f6cd\ufe0f"),
    ("Bills & Utilities", "\U0001f4a1"),
    ("Health", "\U0001f3e5"),
    ("Travel", "\u2708\ufe0f"),
    ("Education", "\U0001f4da"),
    ("Home", "\U0001f3e0"),
    ("Personal Care", "\U0001f487"),
    ("Subscriptions", "\U0001f4f1"),
    ("Income", "\U0001f4b0"),
    ("Other", "\U0001f4cb"),
]
