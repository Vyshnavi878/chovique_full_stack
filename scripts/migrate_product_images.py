import asyncio
from sqlalchemy import text
from app.db.session import async_session_maker

async def migrate():
    print("Starting migration to add 'images' column to 'products' table...")
    async with async_session_maker() as session:
        try:
            # For SQLite (which seems to be the DB based on previous errors in other conversations, though maybe it's PG)
            # We'll use a simple ALTER TABLE
            await session.execute(text("ALTER TABLE products ADD COLUMN images JSON;"))
            await session.commit()
            print("Successfully added 'images' column.")
        except Exception as e:
            await session.rollback()
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("Column 'images' already exists.")
            else:
                print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
