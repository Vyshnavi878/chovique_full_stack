import asyncio
from sqlalchemy import text
from app.db.session import engine

async def migrate():
    alter_statements = [
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS name VARCHAR(100);",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS start_at TIMESTAMPTZ;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS usage_limit INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS per_user_usage_limit INTEGER NOT NULL DEFAULT 1;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS discount_type VARCHAR(50) NOT NULL DEFAULT 'PERCENTAGE';",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS discount_percent DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS discount_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS maximum_discount_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0;",
        "ALTER TABLE coupons ADD COLUMN IF NOT EXISTS minimum_order_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0;"
    ]
    
    for stmt in alter_statements:
        async with engine.begin() as conn:
            try:
                await conn.execute(text(stmt))
                print(f"Executed: {stmt}")
            except Exception as e:
                print(f"Failed (might already exist): {stmt} -> {e}")
                
if __name__ == "__main__":
    asyncio.run(migrate())

