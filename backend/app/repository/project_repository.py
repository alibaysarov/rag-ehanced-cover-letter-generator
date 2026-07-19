from sqlmodel import Session, select,text
from typing import List
from app.database import engine
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.models import Project

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR

import json

class ProjectRepository:
    def __init__(self):
        self._session = Session(engine)
    
    def create_many(
        self,
        user_id: int,
        projects: list[ProjectFromCVModel],
    )->int:
        with self._session as session:
            items = [self._create_project(session,project,user_id) for project in projects]
            session.add_all(items)
            session.commit()
            return len(items)
        
    def get_by_user(self,user_id:int)->list[Project]:
        statement = select(Project).where(Project.user_id == user_id)
        return list(self._session.exec(statement).all())

    
    def search_by_technologies(self,user_id:int, techs: list[str])->list[Project]:
        statement = select(Project).where(Project.technologies.overlap(techs)).where(Project.user_id == user_id)
        return list(self._session.exec(statement).all())
    
    def get_relevant_by_vacancy_data(self,vacancy_data:list[dict]):
        query = text("""
            WITH input_data AS (
                SELECT
                    (elem->>'id')::int AS id,
                    ARRAY(
                        SELECT jsonb_array_elements_text(elem->'technologies')
                    )::text[] AS expected_technologies
                FROM jsonb_array_elements(:vacancy_data) AS elem
            )
            SELECT
                p.id,
                p.name,
                p.technologies,
            FROM projects p
            JOIN input_data i ON i.id = p.id
            WHERE p.technologies && i.expected_technologies
        """)
        
        result = self._session.exec(
            query,
            params={"vacancy_data":json.dumps(vacancy_data)}
        ).all()
        return result
    
    def get_relevant(self, user_id: int, techs: list[str]):
        techs_array = cast(techs, ARRAY(VARCHAR))

        inner = (
            select(func.unnest(Project.technologies))
            .correlate(Project)  # <-- ключевая правка
            .intersect(select(func.unnest(techs_array)))
        )

        match_count = func.cardinality(
            func.array(inner.scalar_subquery())
        ).label("match_count")

        statement = (
            select(Project, match_count)
            .where(Project.technologies.overlap(techs))
            .where(Project.user_id == user_id)
            .order_by(match_count.desc())
        )

        rows = self._session.exec(statement).all()
        return [(project, count) for project, count in rows]
    
    def delete(self,id:int,user_id:int)->None:
        with Session(engine) as session:
            statement = select(Project).where(Project.id ==id).where(Project.user_id == user_id)
            results = session.exec(statement)
            hero = results.one()
            session.delete(hero)

    def _create_project(self,session,dto:ProjectFromCVModel,user_id:int):
        
        normalized_tech:List[str] = [item.lower() for item in dto.technologies] 
        
        return Project(
            name=dto.name, 
            user_id=user_id, 
            web_site=dto.website, 
            skills=dto.skills, 
            achievements=dto.achievements, 
            company_name=dto.name,
            technologies=normalized_tech
        )
        
        
        