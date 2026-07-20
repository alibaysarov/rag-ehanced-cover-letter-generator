# repository/user_repository.py
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session: AsyncSession = session

    async def create_user(
        self,
        email: str,
        password_hash: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        """Create a new user"""
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
        )
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        result = await self._session.execute(statement)

        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return await self._session.get(User, user_id)

    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user fields"""
        user = await self.get_user_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            # Update timestamp
            user.updated_at = datetime.utcnow()

            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
            return user
        return None

    async def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        user = await self.get_user_by_id(user_id)
        if user:
            await self._session.delete(user)
            await self._session.commit()
            return True
        return False
