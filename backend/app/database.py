import logging
from typing import Generator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create engine
engine = create_async_engine(
    url=settings.DATABASE_URL,
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_db() -> Generator[AsyncSession, None, None]:
    """Dependency to get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
