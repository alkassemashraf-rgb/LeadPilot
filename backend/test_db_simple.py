import asyncio
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine

async def test_db():
    try:
        engine = create_async_engine("sqlite+aiosqlite:///./leadpilot.db")
        async with engine.begin() as conn:
            print("Connected to DB")
            await conn.run_sync(SQLModel.metadata.create_all)
            print("Tables checked/created")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_db())
