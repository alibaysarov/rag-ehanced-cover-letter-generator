from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.core.config import settings
from app.middleware.auth import AuthMiddleware
from app.database import init_db, check_db_connection
import logging
from .services.llm.agents.tools.fetch_url import parse_hh
from .services.llm.agents.job_requirement import JobRequirementAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    # Startup
    logger.info("Starting application...")
    
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
    
    # Shutdown
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
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




human = """
        Проанализируй текст вакансии по: {job_text}
        Затем пиши на том языке, на котором информация на странице вакансии.
        item_a = 'Языки программирования'
        item_b='базы данных'
        item_c='dev ops навыки'
        item_d = 'Софт скиллы и прочее'
        Извлеки и суммируй следующую информацию:
        - Название вакансии
        - Название/область проекта
        - Требуемые навыки и компетенции (порядок:[item_a, item_b,item_c,item_d (только значения)])
        Представь информацию в структурированном виде.
        Отвечай на русском языке
"""




