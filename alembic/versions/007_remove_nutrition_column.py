"""remove nutrition column

Revision ID: 007
Revises: 006
Create Date: 2026-08-16 22:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006_is_available'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We use batch_alter_table for SQLite compatibility just in case
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('nutrition')

def downgrade() -> None:
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nutrition', sa.JSON(), nullable=True))
