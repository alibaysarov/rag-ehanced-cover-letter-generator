from typing import Annotated

from fastapi import Depends, HTTPException, WebSocket, WebSocketException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repository.user_repository import UserRepository
from app.schemas.api.user import AuthenticatedUser
from app.services.jwt import JwtService

security = HTTPBearer()


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    token = websocket.query_params.get("token")
    print("token is ")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    if token.startswith("Bearer "):
        token = token.removeprefix("Bearer ")

    jwt_service = JwtService()
    user_repo = UserRepository(db)
    try:
        email = jwt_service.get_email_from_token(token)
        user = await user_repo.get_user_by_email(email)

        if user is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

        if not user.is_active:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

        return AuthenticatedUser.model_validate(user)
    except Exception as e:
        print("error", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    auth_credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AuthenticatedUser:
    """Get current user from JWT token in Authorization header"""
    try:
        if auth_credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jwt_service = JwtService()
        user_repo = UserRepository(db)

        payload = jwt_service.decode_jwt(auth_credentials.credentials)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email = payload.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
            )

        return AuthenticatedUser.model_validate(user)
    except HTTPException:
        raise
    except Exception as e:
        print("error", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]

WsUser = Annotated[AuthenticatedUser, Depends(get_current_user_ws)]
