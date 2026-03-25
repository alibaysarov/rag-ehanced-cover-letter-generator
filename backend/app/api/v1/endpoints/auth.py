# api/v1/auth.py
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlmodel import Session
from typing import Annotated

from app.services.jwt import JwtService
from app.services.password import PasswordService
from app.database import get_db
from app.repository.user_repository import UserRepository
from app.models.user import User
from app.helper.user import CurrentUser, get_current_user, get_user_repository

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool
    is_verified: bool
    created_at: str

# Router and services
router = APIRouter()
jwt_service = JwtService()
password_service = PasswordService()
# security = HTTPBearer()

# Dependencies



# Type alias for cleaner code
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    register_data: RegisterRequest,
    user_repo: UserRepo
):
    """Register a new user"""
    # Check if user already exists
    existing_user = user_repo.get_user_by_email(register_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Hash password
    password_hash = password_service.hash_password(register_data.password)

    # Create user
    try:
        user = user_repo.create_user(
            email=register_data.email,
            password_hash=password_hash,
            first_name=register_data.first_name,
            last_name=register_data.last_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

    # Generate tokens
    access_token = jwt_service.create_access_token(user.email)
    refresh_token = jwt_service.create_refresh_token(user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    user_repo: UserRepo
):
    """Login user and return JWT tokens"""
    # Find user by email
    user = user_repo.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Verify password
    if not password_service.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Generate tokens
    access_token = jwt_service.create_access_token(user.email)
    refresh_token = jwt_service.create_refresh_token(user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(refresh_data: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    try:
        payload = jwt_service.decode_jwt(refresh_data.refresh_token)
        email = payload.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"}
            )

        access_token = jwt_service.create_access_token(email)
        refresh_token = jwt_service.create_refresh_token(email)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Get current user information"""

    user_email = request.state.user_email
    current_user = _get_user_by_mail(user_email,user_repo)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat()
    )

@router.post("/logout")
def logout(current_user: CurrentUser):
    """Logout user (client should discard tokens)"""
    return {"message": "Logged out successfully"}



def _get_user_by_mail(email:str,user_repo: UserRepository):
    current_user = user_repo.get_user_by_email(email)
    return current_user