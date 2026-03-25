from typing import Generator
from sqlmodel import create_engine, Session, SQLModel, text
from app.core.config import settings
import logging
from sqlalchemy.exc import OperationalError
logger = logging.getLogger(__name__)

# Create engine
engine = create_engine(settings.DATABASE_URL)

# engine = create_engine(
#     url=settings.DATABASE_URL,
#     echo=settings.DATABASE_ECHO,
#     pool_size=settings.DATABASE_POOL_SIZE,
#     max_overflow=settings.DATABASE_MAX_OVERFLOW,
#     pool_pre_ping=True,
#     connect_args={"connect_timeout": 10}
# )


def init_db() -> None:
    """Initialize database tables"""
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        raise Exception(
            "Cannot connect to database. Please check:\n"
            "1. PostgreSQL is running\n"
            "2. Database credentials are correct\n"
            "3. Database exists\n"
            f"Connection string: {settings.DATABASE_URL.split('@')[0]}://***@{settings.DATABASE_URL.split('@')[1]}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        logger.info("Database connection check: OK")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()