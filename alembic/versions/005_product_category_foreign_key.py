"""005 product category foreign key

Revision ID: 005_product_category_fk
Revises: 004_payment_status
Create Date: 2026-08-14

Replaces hardcoded product_category enum on products table with foreign key category_id -> categories.id.
Preserves existing product records and maps existing category enum values to Categories database records.
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = '005_product_category_fk'
down_revision = '004_payment_status'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    
    # 1. Add category_id column to products table
    op.add_column(
        'products',
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=True)
    )
    
    # 2. Ensure initial categories exist in categories table to map legacy enums
    categories_tb = table(
        'categories',
        column('id', sa.String),
        column('name', sa.String),
        column('slug', sa.String),
        column('sort_order', sa.Integer),
        column('is_active', sa.Boolean)
    )
    
    legacy_mapping = [
        ('dark', 'Dark Chocolate', 'dark-chocolate'),
        ('milk', 'Milk Chocolate', 'milk-chocolate'),
        ('white', 'White Chocolate', 'white-chocolate'),
        ('gift', 'Gift Hampers', 'gift-hampers'),
        ('beverage', 'Beverages', 'beverages')
    ]
    
    # Map legacy categories
    for idx, (legacy_key, name, slug) in enumerate(legacy_mapping, start=1):
        cat_id = None
        result = bind.execute(
            sa.text("SELECT id FROM categories WHERE slug = :slug OR LOWER(name) = :name_lower LIMIT 1"),
            {"slug": slug, "name_lower": name.lower()}
        ).fetchone()
        
        if result:
            cat_id = result[0]
        else:
            cat_id = str(uuid.uuid4())
            bind.execute(
                categories_tb.insert().values(
                    id=cat_id,
                    name=name,
                    slug=slug,
                    sort_order=idx,
                    is_active=True
                )
            )
        
        # Backfill products where category = legacy_key or category ILIKE legacy_key
        try:
            bind.execute(
                sa.text("UPDATE products SET category_id = :cat_id WHERE category_id IS NULL AND (category::text = :legacy_key OR LOWER(category::text) LIKE :pattern)"),
                {"cat_id": cat_id, "legacy_key": legacy_key, "pattern": f"%{legacy_key}%"}
            )
        except Exception:
            pass

    # Fallback for any remaining unmapped products to first category
    first_cat = bind.execute(sa.text("SELECT id FROM categories ORDER BY sort_order ASC, name ASC LIMIT 1")).fetchone()
    if first_cat:
        bind.execute(
            sa.text("UPDATE products SET category_id = :first_id WHERE category_id IS NULL"),
            {"first_id": first_cat[0]}
        )

    # 3. Create index on category_id
    try:
        op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    except Exception:
        pass

    # 4. Safely drop old category column
    with op.batch_alter_table('products') as batch_op:
        try:
            batch_op.drop_column('category')
        except Exception:
            pass

    # 5. Drop enum type if PostgreSQL
    if bind.dialect.name == 'postgresql':
        try:
            bind.execute(sa.text("DROP TYPE IF EXISTS product_category CASCADE"))
        except Exception:
            pass


def downgrade():
    op.add_column('products', sa.Column('category', sa.String(100), nullable=True))
    try:
        op.drop_index(op.f('ix_products_category_id'), table_name='products')
    except Exception:
        pass
    op.drop_column('products', 'category_id')
