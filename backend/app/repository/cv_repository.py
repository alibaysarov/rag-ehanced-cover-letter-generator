from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.schemas.general import Option
from ..models.cv import CV



class CVRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_cv(self, user_id: int, source_id: int, filename: str, original_filename: str,
                       file_size: int, content_type: str, file_path: Optional[str] = None,
                       upload_ip: Optional[str] = None, user_agent: Optional[str] = None) -> CV:
        """Create a new CV record"""
        cv = CV(
            user_id=user_id,
            source_id=source_id,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            content_type=content_type,
            upload_ip=upload_ip,
            user_agent=user_agent
        )
        self.session.add(cv)
        self.session.commit()
        self.session.refresh(cv)
        return cv
    async def update_cv(self, cv: CV,data: dict) -> CV:
        """Update an existing CV record"""
        cv.sqlmodel_update(data)
        self.session.add(cv)
        return cv
    async def get_cv_by_source_id(self, source_id: int) -> Optional[CV]:
        """Get CV by source_id"""
        stmt = select(CV).where(CV.source_id == source_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cv_by_id(self, cv_id: int) -> Optional[CV]:
        """Get CV by ID"""
        stmt = select(CV).where(CV.id == cv_id)
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_cvs_options_by_user_id(self, user_id: int) -> list[Option]:
        """Get all CV options for a user"""
        stmt = select(CV.source_id, CV.filename).where(CV.user_id == user_id)
        result = self.session.execute(stmt)
        
        return [
            {"name": row.filename, "value": row.source_id}
            for row in result.all()
        ]
    async def get_cvs_by_user_id(self, user_id: int) -> list[CV]:
        """Get all CVs for a user"""
        stmt = select(CV).where(CV.user_id == user_id)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_cv_status(self, cv_id: int, status: str) -> bool:
        """Update CV status"""
        cv = await self.get_cv_by_id(cv_id)
        if cv:
            cv.status = status
            await self.session.commit()
            return True
        return False
    def delete_cv(self, cv: CV):
        """Delete CV record and return it for rollback if needed"""
        if cv is not None:
            self.session.delete(cv)
            # self.session.flush()
            return cv