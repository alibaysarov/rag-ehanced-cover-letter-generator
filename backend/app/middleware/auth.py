from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services import JwtService

jwt_service = JwtService()
UNPROTECTED_ROUTES = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    # "/api/v1/letter/async-test"
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем health check и некоторые другие эндпоинты
        if request.url.path in UNPROTECTED_ROUTES:
            return await call_next(request)

        # Проверяем авторизацию для API эндпоинтов
        if request.url.path.startswith("/api/v1/"):
            token = None

            if (
                request.url.path.startswith("/api/v1/auto-parse/stream/")
                or "/generate-stream" in request.url.path
            ):
                token = request.query_params.get("token")
                if not token:
                    return JSONResponse(
                        status_code=401, content={"detail": "Token query param missing"}
                    )

                request.state.user_email = _get_email_from_token(token=token)
                _set_auth_header(request=request, token=token)
                response = await call_next(request)
                return response
            else:
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authorization header missing or invalid"},
                    )
                token = auth_header.split(" ")[1]

            try:
                # Можно добавить payload в request.state для использования в эндпоинтах
                request.state.user_email = _get_email_from_token(token=token)
            except Exception as e:
                return JSONResponse(
                    status_code=401, content={"detail": "Invalid or expired token"}
                )

        response = await call_next(request)
        return response


def _get_email_from_token(token: str) -> str:
    payload = jwt_service.decode_jwt(token)
    email = payload.get("email")
    if not email:
        raise ValueError("Token payload missing 'email' claim")
    return email


def _set_auth_header(request: Request, token: str) -> None:
    new_headers = [(k, v) for k, v in request.scope["headers"] if k != b"Authorization"]
    new_headers.append((b"Authorization", f"Bearer {token}".encode()))
    request.scope["headers"] = new_headers
