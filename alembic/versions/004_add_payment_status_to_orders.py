"""004 add payment_status to orders

Revision ID: 004_payment_status
Revises: 003_add_wallets_and_order_coins
Create Date: 2026-08-10

Adds a separate payment_status column to the orders table so that
payment lifecycle (PENDING / PAID / FAILED / REFUNDED) is tracked
independently from fulfillment status (Processing / Shipped / Delivered …).

Backfill rules:
  - Cash on Delivery orders → PENDING (payment not yet collected)
  - All other payment methods → PAID   (simulated successful payment)
  - Cancelled orders         → FAILED  (or PENDING if COD)
"""
from alembic import op
import sqlalchemy as sa

revision = '004_payment_status'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add payment_status column with a server default of 'PENDING'
    op.add_column(
        'orders',
        sa.Column('payment_status', sa.String(50), nullable=False, server_default='PENDING'),
    )

    # Backfill: online payment methods → PAID
    op.execute(
        """
        UPDATE orders
        SET payment_status = 'PAID'
        WHERE payment_method NOT IN ('Cash on Delivery', 'COD', 'Cash On Delivery')
          AND status != 'Cancelled'
        """
    )

    # COD + non-cancelled → PENDING (already set by server default, but explicit)
    op.execute(
        """
        UPDATE orders
        SET payment_status = 'PENDING'
        WHERE payment_method IN ('Cash on Delivery', 'COD', 'Cash On Delivery')
          AND status != 'Cancelled'
        """
    )

    # Cancelled orders with online payment → FAILED
    op.execute(
        """
        UPDATE orders
        SET payment_status = 'FAILED'
        WHERE status = 'Cancelled'
          AND payment_method NOT IN ('Cash on Delivery', 'COD', 'Cash On Delivery')
        """
    )

    # Cancelled COD → keep PENDING (payment was never collected anyway)


def downgrade():
    op.drop_column('orders', 'payment_status')
