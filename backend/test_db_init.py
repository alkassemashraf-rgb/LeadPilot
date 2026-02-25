import asyncio
import logging
import sys
import os

# Ensure we can import from backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.db import engine
from sqlmodel import SQLModel
from app.core.seed import seed_modules

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_init():
    logger.info("Starting isolated DB init test...")
    try:
        logger.info("Initializing metadata...")
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Metadata initialized.")
        
        logger.info("Seeding modules...")
        await seed_modules()
        logger.info("Modules seeded.")
    except Exception as e:
        logger.error(f"Error during init: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_init())
