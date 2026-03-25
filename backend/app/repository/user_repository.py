# repository/user_repository.py
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_user(
        self, 
        email: str, 
        password_hash: str, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """Create a new user"""
        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        statement = select(User).where(User.email == email)
        return self.session.exec(statement).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.session.get(User, user_id)

    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user fields"""
        user = self.get_user_by_id(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            # Update timestamp
            user.updated_at = datetime.utcnow()
            
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
            return user
        return None

    def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            return True
        return False

    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate user account"""
        return self.update_user(user_id, is_active=False)

    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate user account"""
        return self.update_user(user_id, is_active=True)

    def verify_user(self, user_id: int) -> Optional[User]:
        """Mark user as verified"""
        return self.update_user(user_id, is_verified=True)

    def get_all_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination"""
        statement = select(User).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users"""
        statement = select(User).where(User.is_active == True).offset(skip).limit(limit)
        return self.session.exec(statement).all()