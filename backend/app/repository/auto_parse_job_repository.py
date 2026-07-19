from sqlmodel import Session, select
from app.database import engine
from app.models import AutoParsedJob
from sqlmodel import Session, select, desc,func
from app.schemas import AutoParseResponse
class AutoParseJobRepository:
    def __init__(self):
        self._session = Session(engine)
    
    
    def get_by_id(self,id:int)->AutoParsedJob|None:
        statement = select(AutoParsedJob).where(AutoParsedJob.id == id)
        job = self._session.exec(statement).one_or_none()
        return job
    
    def get_by_job_id(self,job_id:int):    
        statement = select(AutoParsedJob).where(AutoParsedJob.parsing_job_id == job_id)
        return list(self._session.exec(statement).all())
    
    def get_last_id(self,parsing_job_id:int)->int|None:
        stmt = select(AutoParsedJob.id).where(AutoParsedJob.parsing_job_id == parsing_job_id).order_by(desc(AutoParsedJob.id))
        job = self._session.exec(stmt).one_or_none()
        return job
    
    def get_generation_status_info(self,parsing_job_id:int)->AutoParseResponse:
        """
        Метод Берет из бд общее число вакансий и то число которое уже сгенерировано
        """
        
        total_select =(
            select(func.count(AutoParsedJob.id))
            .where(AutoParsedJob.parsing_job_id == parsing_job_id).scalar_subquery()
        )
        generated_select =(
            select(func.count(AutoParsedJob.id))
            .where(AutoParsedJob.parsing_job_id == parsing_job_id)
            .where(AutoParsedJob.is_generated == True).scalar_subquery()
        )
        stmt = select(
            total_select.label("total"),
            generated_select.label("generated")   
        )
        result = self.session.execute(stmt)
        row = result.one()
        return AutoParseResponse(total=row.total, generated=row.generated)

    
    def update_vacancy(self,id:int,letter_text:str,is_generated:bool):
        with self._session as db:
            v = db.get(AutoParsedJob, id)
            if v:
                v.cover_letter_text = letter_text
                v.is_generated = is_generated
                db.add(v)
                db.commit()
