"""Rename the former best-before field to storage date."""

from alembic import op


revision = "0002_storage_date"
down_revision = "0001_postgres_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_items_best_before", table_name="items")
    op.alter_column("items", "best_before", new_column_name="storage_date")
    op.create_index("ix_items_storage_date", "items", ["storage_date"])


def downgrade() -> None:
    op.drop_index("ix_items_storage_date", table_name="items")
    op.alter_column("items", "storage_date", new_column_name="best_before")
    op.create_index("ix_items_best_before", "items", ["best_before"])
