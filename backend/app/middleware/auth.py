from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.jwt import JwtService

jwt_service = JwtService()

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Пропускаем health check и некоторые другие эндпоинты
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/auth/register","/api/v1/auth/login"]:
            return await call_next(request)

        # Проверяем авторизацию для API эндпоинтов
        if request.url.path.startswith("/api/v1/"):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing or invalid"}
                )

            token = auth_header.split(" ")[1]

            try:
                # Декодируем токен (здесь можно добавить дополнительную логику)
                payload = jwt_service.decode_jwt(token)
                # Можно добавить payload в request.state для использования в эндпоинтах
                request.state.user_email = payload.get("email")
            except Exception as e:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or expired token"}
                )

        response = await call_next(request)
        return response