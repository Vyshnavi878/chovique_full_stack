"""add user_wallets coin_transactions and order coin columns

Revision ID: 003
Revises: 002
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_wallets table
    op.create_table(
        "user_wallets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("coin_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_user_wallets_user_id", "user_wallets", ["user_id"])

    # Create coin_transactions table
    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("coins", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_coin_transactions_user_id", "coin_transactions", ["user_id"])
    op.create_index("ix_coin_transactions_order_id", "coin_transactions", ["order_id"])

    # Add new columns to orders table
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("coupon_discount", sa.Float(), nullable=False, server_default="0.0"))
    op.add_column("orders", sa.Column("coins_used", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("coin_discount", sa.Float(), nullable=False, server_default="0.0"))
    op.add_column("orders", sa.Column("coins_earned", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("orders", "coins_earned")
    op.drop_column("orders", "coin_discount")
    op.drop_column("orders", "coins_used")
    op.drop_column("orders", "coupon_discount")
    op.drop_column("orders", "coupon_code")
    op.drop_table("coin_transactions")
    op.drop_table("user_wallets")
