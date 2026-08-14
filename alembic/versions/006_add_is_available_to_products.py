"""006 add is_available to products

Revision ID: 006_is_available
Revises: 005_product_category_fk
Create Date: 2026-08-14

Adds is_available boolean column to products table to decouple customer availability status from stored stock inventory quantity.
"""
from alembic import op
import sqlalchemy as sa

revision = '006_is_available'
down_revision = '005_product_category_fk'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'products',
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true')
    )


def downgrade():
    op.drop_column('products', 'is_available')
