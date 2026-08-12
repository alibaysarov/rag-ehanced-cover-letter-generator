import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.cache import redis as redis_db
from app.core.config import settings
from app.database import check_db_connection
from app.dependencies import get_pub_sub_listener
from app.middleware.auth import AuthMiddleware
from app.pw_instances.chromium import close_browser, start_browser
from app.tasks import listener

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("Starting application...")
    await redis_db.connect_redis()

    await start_browser()
    pubsub_listener = get_pub_sub_listener()
    print("starting listeners", listener)
    pubsub_listener.start_all_listeners()
    print("Ln count", len(pubsub_listener._listeners))

    # Check database connection
    conn_result = await check_db_connection()
    if not conn_result:
        logger.error("Failed to connect to database on startup")
        raise Exception("Database connection failed")

    yield

    pubsub_listener.stop_all_listeners()

    await redis_db.close_conn()
    await close_browser()
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
)


app.add_middleware(AuthMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}
