import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Cover Letter RAG"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "AI-powered cover letter generator using RAG"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM="HS256"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5173/",
        "http://localhost:3000",
        "http://localhost:3000/",
    ]

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # PostgreSQL Database
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cover_letter_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "secure_password_123")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cover_letter_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")  # Use localhost for direct connection
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    # Database URL (constructed from individual vars or override)
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Qdrant
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")

    # Database settings
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))


settings = Settings()
