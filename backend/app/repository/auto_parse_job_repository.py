
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import AutoParsedJob


class AutoParseJobRepository:
    def __init__(self,session:AsyncSession):
        self._session = session
    
    async def create(self,**kwargs)->AutoParsedJob:
        auto_parse_job = AutoParsedJob(**kwargs)
        self._session.add(auto_parse_job)
        await self._session.commit()
        await self._session.refresh(auto_parse_job)
        return auto_parse_job
        
    
    async def get_by_id(self,id:int)->AutoParsedJob|None:
        statement = select(AutoParsedJob).where(AutoParsedJob.id == id)
        result = await self._session.execute(statement)
        job = result.one_or_none()
        return job
    
    async def get_by_job_id(self,job_id:int):    
        statement = select(AutoParsedJob).where(AutoParsedJob.parsing_job_id == job_id)
        result = await self._session.execute(statement)
        return list(result.all())
    
    
    
    async def update_vacancy(self,id:int,letter_text:str,is_generated:bool)->AutoParsedJob:
        
        vacancy = await self._session.get(AutoParsedJob, id)
        if vacancy:
            vacancy.cover_letter_text = letter_text
            vacancy.is_generated = is_generated
            self._session.add(vacancy)
            await self._session.commit()
            await self._session.refresh(vacancy)
        return vacancy
