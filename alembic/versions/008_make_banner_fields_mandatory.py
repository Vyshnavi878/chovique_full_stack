"""make banner fields mandatory

Revision ID: 008
Revises: 007
Create Date: 2026-08-16 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Update NULL values to empty strings before making columns NOT NULL
    op.execute("UPDATE banners SET subtitle = '' WHERE subtitle IS NULL")
    op.execute("UPDATE banners SET tag = '' WHERE tag IS NULL")
    op.execute("UPDATE banners SET button_text = '' WHERE button_text IS NULL")
    op.execute("UPDATE banners SET link = '' WHERE link IS NULL")

    with op.batch_alter_table('banners', schema=None) as batch_op:
        batch_op.alter_column('subtitle', existing_type=sa.TEXT(), nullable=False)
        batch_op.alter_column('tag', existing_type=sa.VARCHAR(length=255), nullable=False)
        batch_op.alter_column('button_text', existing_type=sa.VARCHAR(length=100), nullable=False)
        batch_op.alter_column('link', existing_type=sa.VARCHAR(length=500), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('banners', schema=None) as batch_op:
        batch_op.alter_column('subtitle', existing_type=sa.TEXT(), nullable=True)
        batch_op.alter_column('tag', existing_type=sa.VARCHAR(length=255), nullable=True)
        batch_op.alter_column('button_text', existing_type=sa.VARCHAR(length=100), nullable=True)
        batch_op.alter_column('link', existing_type=sa.VARCHAR(length=500), nullable=True)
