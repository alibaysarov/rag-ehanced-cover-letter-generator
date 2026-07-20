# api/v1/auth.py
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.dependencies import (
    DBSession,
    get_jwt_service,
    get_password_service,
    get_user_repository,
)
from app.helper.user import CurrentUser
from app.repository.user_repository import UserRepository
from app.services import JwtService, PasswordService


# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    password: str


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


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


# Router
router = APIRouter()

# Type alias for cleaner code
UserRepo = Annotated[UserRepository, Depends(get_user_repository)]


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    register_data: RegisterRequest,
    user_repo: UserRepo,
    jwt_service: JwtService = Depends(get_jwt_service),
    password_service: PasswordService = Depends(get_password_service),
):
    """Register a new user"""
    # Check if user already exists
    existing_user = user_repo.get_user_by_email(register_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Hash password
    password_hash = password_service.hash_password(register_data.password)

    # Create user
    try:
        user = await user_repo.create_user(
            email=register_data.email,
            password_hash=password_hash,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

    # Generate tokens
    access_token = jwt_service.create_access_token(user.email)
    refresh_token = jwt_service.create_refresh_token(user.email)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    user_repo: UserRepo,
    jwt_service: JwtService = Depends(get_jwt_service),
    password_service: PasswordService = Depends(get_password_service),
):
    """Login user and return JWT tokens"""
    # Find user by email
    user = await user_repo.get_user_by_email(login_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
        )

    # Verify password
    if not password_service.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = jwt_service.create_access_token(user.email)
    refresh_token = jwt_service.create_refresh_token(user.email)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    jwt_service: JwtService = Depends(get_jwt_service),
):
    """Refresh access token using refresh token"""
    try:
        payload = jwt_service.decode_jwt(refresh_data.refresh_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email = payload.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = jwt_service.create_access_token(email)
        refresh_token = jwt_service.create_refresh_token(email)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(user: CurrentUser):
    """Get current user information"""

    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user_info(
    update_data: UpdateProfileRequest,
    user_repo: UserRepo,
    user: CurrentUser,
    db: DBSession,
):

    fields = update_data.model_dump(exclude_unset=True)

    new_email = fields.get("email")
    if new_email and new_email != user.email:
        existing = await user_repo.get_user_by_email(new_email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already taken",
            )

    updated_user = await user_repo.update_user(user.id, **fields)
    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        is_active=updated_user.is_active,
        is_verified=updated_user.is_verified,
        created_at=updated_user.created_at.isoformat(),
    )


@router.post("/change-password")
async def change_password(
    user: CurrentUser,
    payload: ChangePasswordRequest,
    user_repo: UserRepo,
    password_service: PasswordService = Depends(get_password_service),
):
    """Change current user password"""

    if not password_service.verify_password(
        payload.current_password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password",
        )

    new_hash = password_service.hash_password(payload.new_password)
    await user_repo.update_user(user.id, password_hash=new_hash)

    return {"message": "Password updated successfully"}


@router.post("/logout")
def logout(user: CurrentUser):
    """Logout user (client should discard tokens)"""
    return {"message": "Logged out successfully"}
