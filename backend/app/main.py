from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.core.config import settings
from app.middleware.auth import AuthMiddleware
from app.database import init_db, check_db_connection
import logging
import aioredis



from app.cache import redis as redis_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("Starting application...")
    await redis_db.connect_redis()
    # Check database connection
    if not check_db_connection():
        logger.error("Failed to connect to database on startup")
        raise Exception("Database connection failed")
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    await redis_db.close_conn()
    
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)




@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/redis-test")
async def redis_test():
    await redis_db.redis_client.set("key","value")
    
    
    cache_hit = await redis_db.redis_client.get("key")
    
    return {"message":cache_hit}

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






