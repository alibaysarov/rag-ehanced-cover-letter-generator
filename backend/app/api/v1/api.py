from fastapi import APIRouter

from app.api.v1.endpoints import auth, cv, letter, parse, projects, user
from app.api.v1.endpoints.auto_parse_router import router as auto_parse_router
from app.api.v1.endpoints.stats import router as stats_router

api_router = APIRouter()

# Include letter endpoints
api_router.include_router(
    letter.router,
    prefix="/letter",
    tags=["letter"]
)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"]
)
api_router.include_router(
    user.router,
    prefix="/user",
    tags=["user"]
)
api_router.include_router(
    cv.router,
    prefix="/cv",
    tags=["cv"]
)
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["projects"]
)
api_router.include_router(
    parse.router,
    prefix="/parse",
    tags=["parse"]
)
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(auto_parse_router, prefix="/auto-parse", tags=["auto-parse"])