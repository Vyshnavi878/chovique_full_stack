"""add cancellation, return, and updated_at columns to orders

Revision ID: 010
Revises: 009
Create Date: 2026-08-19 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('orders')]

    if 'delivered_at' not in existing_columns:
        op.add_column('orders', sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
    if 'cancelled_at' not in existing_columns:
        op.add_column('orders', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    if 'cancellation_reason' not in existing_columns:
        op.add_column('orders', sa.Column('cancellation_reason', sa.Text(), nullable=True))
    if 'returned_at' not in existing_columns:
        op.add_column('orders', sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True))
    if 'return_reason' not in existing_columns:
        op.add_column('orders', sa.Column('return_reason', sa.Text(), nullable=True))
    if 'updated_at' not in existing_columns:
        op.add_column('orders', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('orders', 'updated_at')
    op.drop_column('orders', 'return_reason')
    op.drop_column('orders', 'returned_at')
    op.drop_column('orders', 'cancellation_reason')
    op.drop_column('orders', 'cancelled_at')
    op.drop_column('orders', 'delivered_at')
