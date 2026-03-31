"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(100), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="UYU"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # Accounts
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("institution", sa.String(100), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("last_four", sa.String(4), nullable=True),
        sa.Column("currencies", sa.JSON(), nullable=False, server_default='["UYU", "USD"]'),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Cards
    op.create_table(
        "cards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("card_type", sa.String(10), nullable=False),
        sa.Column("institution", sa.String(100), nullable=False),
        sa.Column("last_four", sa.String(4), nullable=True),
        sa.Column("currencies", sa.JSON(), nullable=False, server_default='["UYU", "USD"]'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False, server_default=""),
        sa.Column("parent_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Expenses
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("card_id", sa.Uuid(), sa.ForeignKey("cards.id"), nullable=True),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UYU"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("merchant", sa.String(200), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("input_method", sa.String(20), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("receipt_image_url", sa.String(500), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("is_reconciled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Expense Items
    op.create_table(
        "expense_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("expense_id", sa.Uuid(), sa.ForeignKey("expenses.id"), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(8, 2), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Splits
    op.create_table(
        "splits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("expense_id", sa.Uuid(), sa.ForeignKey("expenses.id"), nullable=False),
        sa.Column("person_name", sa.String(100), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_settled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Budgets
    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UYU"),
        sa.Column("period", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Bank Statements
    op.create_table(
        "bank_statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("statement_month", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Statement Transactions
    op.create_table(
        "statement_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("statement_id", sa.Uuid(), sa.ForeignKey("bank_statements.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UYU"),
        sa.Column("matched_expense_id", sa.Uuid(), sa.ForeignKey("expenses.id"), nullable=True),
        sa.Column("match_status", sa.String(20), nullable=False, server_default="unmatched"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Seed default categories
    import uuid
    categories_table = sa.table(
        "categories",
        sa.column("id", sa.Uuid),
        sa.column("user_id", sa.Uuid),
        sa.column("name", sa.String),
        sa.column("icon", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    default_categories = [
        {"id": uuid.uuid4(), "user_id": None, "name": "Food & Dining", "icon": "\U0001f354", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Groceries", "icon": "\U0001f6d2", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Transport", "icon": "\U0001f68c", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Entertainment", "icon": "\U0001f3ac", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Shopping", "icon": "\U0001f6cd\ufe0f", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Bills & Utilities", "icon": "\U0001f4a1", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Health", "icon": "\U0001f3e5", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Travel", "icon": "\u2708\ufe0f", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Education", "icon": "\U0001f4da", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Home", "icon": "\U0001f3e0", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Personal Care", "icon": "\U0001f487", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Subscriptions", "icon": "\U0001f4f1", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Income", "icon": "\U0001f4b0", "is_active": True},
        {"id": uuid.uuid4(), "user_id": None, "name": "Other", "icon": "\U0001f4cb", "is_active": True},
    ]
    op.bulk_insert(categories_table, default_categories)


def downgrade() -> None:
    op.drop_table("statement_transactions")
    op.drop_table("bank_statements")
    op.drop_table("budgets")
    op.drop_table("splits")
    op.drop_table("expense_items")
    op.drop_table("expenses")
    op.drop_table("categories")
    op.drop_table("cards")
    op.drop_table("accounts")
    op.drop_index("ix_users_telegram_id", "users")
    op.drop_table("users")
