"""Create the installation's default user if it does not exist."""

from __future__ import annotations

import asyncio
import os

from sqlmodel import select

from app.database import async_session_maker
from app.models import User
from app.repository.user_repository import UserRepository
from app.services.password import PasswordService


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} must be set in .env")
    return value


async def seed_default_user() -> tuple[int, bool]:
    email = required_env("DEFAULT_USER_EMAIL").lower()
    password = required_env("DEFAULT_USER_PASSWORD")
    if len(password) < 8:
        raise ValueError("DEFAULT_USER_PASSWORD must contain at least 8 characters")

    first_name = os.getenv("DEFAULT_USER_FIRST_NAME", "").strip() or None
    last_name = os.getenv("DEFAULT_USER_LAST_NAME", "").strip() or None

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is not None:
            if user.id is None:
                raise RuntimeError("Existing default user has no database id")
            return user.id, False

        user = await UserRepository(session).create_user(
            email=email,
            password_hash=PasswordService().hash_password(password),
            first_name=first_name,
            last_name=last_name,
        )
        user.is_verified = True
        await session.commit()
        return user.id, True


async def main() -> None:
    user_id, created = await seed_default_user()
    action = "created" if created else "already exists"
    print(f"Default user {action}: id={user_id}")


if __name__ == "__main__":
    asyncio.run(main())
