import asyncio
import logging
from app.database.models import Models
from app.logger import configure_logging

# Configure logging
configure_logging()
logger = logging.getLogger('init_db')

async def main():
    logger.info("Initializing database tables...")
    try:
        models = Models()
        await models.init_tables()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
