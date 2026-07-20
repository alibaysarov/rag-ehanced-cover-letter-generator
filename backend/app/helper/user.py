from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.dependencies import get_jwt_service, get_user_repository
from app.models.user import User
from app.repository.user_repository import UserRepository
from app.schemas.api.user import AuthenticatedUser
from app.services import JwtService

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    jwt_service: JwtService = Depends(get_jwt_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Get current user from JWT token in Authorization header"""
    try:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )

        payload = jwt_service.decode_jwt(credentials)
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user = await user_repo.get_user_by_email(email)
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
        
        return AuthenticatedUser.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        print("error",e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]