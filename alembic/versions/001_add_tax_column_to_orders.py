"""add tax column to orders

Revision ID: 001
Revises:
Create Date: 2026-08-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("tax", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("orders", "tax")
