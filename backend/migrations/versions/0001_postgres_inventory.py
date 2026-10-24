"""Create PostgreSQL inventory schema."""
from alembic import op
import sqlalchemy as sa

revision = "0001_postgres_inventory"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("units", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(80), nullable=False, unique=True), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("warehouses", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("location", sa.String(255)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(32), nullable=False, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("quantity_value", sa.Numeric(12, 3), nullable=False), sa.Column("best_before", sa.Date()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id")), sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id"), nullable=False))
    op.create_index("ix_items_best_before", "items", ["best_before"])

def downgrade() -> None:
    op.drop_table("items"); op.drop_table("warehouses"); op.drop_table("units")
