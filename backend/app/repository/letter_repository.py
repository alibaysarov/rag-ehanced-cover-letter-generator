from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from ..models.letter import Letter


class LetterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_letter(self, cv_id: int, source_id: int, job_title: str,
                           letter_content: str, job_description: Optional[str] = None,
                           company_name: Optional[str] = None, job_url: Optional[str] = None,
                           job_requirements: Optional[str] = None, generation_time: Optional[int] = None,
                           model_used: str = "gpt-4o", status: str = "generated") -> Letter:
        """Create a new letter record"""
        letter = Letter(
            cv_id=cv_id,
            source_id=source_id,
            job_title=job_title,
            job_description=job_description,
            company_name=company_name,
            job_url=job_url,
            letter_content=letter_content,
            job_requirements=job_requirements,
            generation_time=generation_time,
            model_used=model_used,
            status=status
        )
        self.session.add(letter)
        await self.session.commit()
        await self.session.refresh(letter)
        return letter

    async def get_letters_by_source_id(self, source_id: int) -> List[Letter]:
        """Get all letters for a source_id"""
        stmt = select(Letter).where(Letter.source_id == source_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_letter_by_id(self, letter_id: int) -> Optional[Letter]:
        """Get letter by ID"""
        stmt = select(Letter).where(Letter.id == letter_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_letters_by_cv_id(self, cv_id: int) -> List[Letter]:
        """Get all letters for a CV"""
        stmt = select(Letter).where(Letter.cv_id == cv_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
