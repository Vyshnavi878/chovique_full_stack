"""enhance reviews and testimonials

Revision ID: 002
Revises: 001
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status and updated_at to product_reviews
    op.add_column(
        "product_reviews",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="approved"),
    )
    op.add_column(
        "product_reviews",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )

    # Add user_id, status, updated_at to testimonials
    op.add_column(
        "testimonials",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "testimonials",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="approved"),
    )
    op.add_column(
        "testimonials",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("testimonials", "updated_at")
    op.drop_column("testimonials", "status")
    op.drop_column("testimonials", "user_id")
    op.drop_column("product_reviews", "updated_at")
    op.drop_column("product_reviews", "status")
