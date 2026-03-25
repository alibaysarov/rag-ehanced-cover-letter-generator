from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, HttpUrl
from sqlmodel import Session
from typing import Annotated

from app.services.jwt import JwtService
from app.services.password import PasswordService
from app.database import get_db
from app.repository.user_repository import UserRepository
from app.models.user import User


security = HTTPBearer()


def get_jwt_service() -> JwtService:
    """Dependency to get JwtService instance"""
    return JwtService()


def get_user_repository(session: Session = Depends(get_db)) -> UserRepository:
    """Dependency to get UserRepository with database session"""
    return UserRepository(session)

def get_security()->HTTPAuthorizationCredentials:
    return HTTPBearer()

def get_current_user(
    jwt_service: JwtService = Depends(get_jwt_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Get current user from JWT token"""
    try:
        payload = jwt_service.decode_jwt(security.credentials)
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user = user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        print("error",e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


CurrentUser = Annotated[User, Depends(get_current_user)]