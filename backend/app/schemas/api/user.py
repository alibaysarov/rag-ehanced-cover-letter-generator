from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuthenticatedUser(BaseModel):
    """Представление пользователя, который точно существует в БД (прошёл аутентификацию)"""
    model_config = ConfigDict(from_attributes=True)

    id: int  # не Optional — раз юзер аутентифицирован, id всегда есть
    email: str
    is_active: bool
    is_verified: bool
    first_name: Optional[str] = None
    password_hash:str
    last_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime