import json
import logging
from typing import List

from sqlalchemy import cast, func, literal
from sqlalchemy.dialects.postgresql import ARRAY, VARCHAR
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select, text

from app.models import Project
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.schemas.project import RelevantProjectResponse

logger = logging.getLogger(__name__)


class ProjectRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_many(
        self,
        user_id: int,
        projects: list[ProjectFromCVModel],
    ) -> int:
        items = [self._create_project(project, user_id) for project in projects]
        self._session.add_all(items)
        await self._session.commit()
        return len(items)

    async def get_by_user(self, user_id: int) -> list[Project]:
        statement = (
            select(Project).where(Project.user_id == user_id).order_by(Project.id)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, project_id: int, user_id: int) -> Project | None:
        statement = (
            select(Project)
            .where(Project.id == project_id)
            .where(Project.user_id == user_id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def update(
        self,
        project_id: int,
        user_id: int,
        dto: ProjectFromCVModel,
    ) -> Project | None:
        project = await self.get_by_id(project_id, user_id)
        if project is None:
            return None

        project.name = dto.name
        project.company_name = dto.name
        project.web_site = dto.website
        project.skills = dto.skills
        project.achievements = dto.achievements
        project.technologies = [item.lower() for item in dto.technologies]
        self._session.add(project)
        await self._session.commit()
        await self._session.refresh(project)
        return project

    async def get_projects_by_vacancy_text(
        self, vacancy_text: str, user_id: int
    ) -> list[RelevantProjectResponse]:
        """
        Берет текст вакансии и при помощи векторного поиска подбирает релевантные проекты
        """

        try:
            tech = func.unnest(Project.technologies).alias("tech")

            match_count = (
                select(func.count().label("cnt"))
                .select_from(tech)
                .where(
                    func.to_tsvector(
                        "simple",
                        func.lower(literal(vacancy_text)),
                    ).op("@@")(
                        func.plainto_tsquery(
                            "simple",
                            tech.column,
                        )
                    )
                )
                .correlate(Project)
                .lateral()
                .alias("matched")
            )

            statement = (
                select(
                    Project.id,
                    Project.name,
                    Project.company_name.label("project_name"),
                    Project.technologies,
                    match_count.c.cnt.label("match_count"),
                )
                .select_from(Project)
                .join(
                    match_count,
                    literal(True),
                )
                .where(
                    Project.user_id == user_id,
                    match_count.c.cnt > 0,
                )
                .order_by(
                    match_count.c.cnt.desc(),
                )
                .limit(10)
            )

            result = await self._session.execute(statement)

            rows = result.all()

            return [
                RelevantProjectResponse(
                    id=row.id,
                    name=row.name,
                    project_name=row.project_name,
                    technologies=row.technologies,
                )
                for row in rows
            ]

        except Exception as e:
            logger.error("Error during fetching relevant projects", exc_info=True)
            return []

    async def get_relevant_by_vacancy_data(self, vacancy_data: list[dict]):
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

        result = await self._session.execute(
            query, params={"vacancy_data": json.dumps(vacancy_data)}
        )
        return list(result.all())

    async def get_relevant(self, user_id: int, techs: list[str]):
        techs_array = cast(techs, ARRAY(VARCHAR))

        inner = (
            select(func.unnest(Project.technologies))
            .correlate(Project)  # <-- ключевая правка
            .intersect(select(func.unnest(techs_array)))
        )

        match_count = func.cardinality(func.array(inner.scalar_subquery())).label(
            "match_count"
        )

        statement = (
            select(Project, match_count)
            .where(Project.technologies.overlap(techs))
            .where(Project.user_id == user_id)
            .order_by(match_count.desc())
        )

        result = await self._session.execute(statement)
        rows = result.all()
        return [(project, count) for project, count in rows]

    async def search_contexts(
        self, user_id: int, query: str, top_k: int = 5
    ) -> list[Project]:
        project_text = func.concat_ws(
            " ",
            Project.name,
            Project.company_name,
            func.array_to_string(Project.technologies, " "),
            func.array_to_string(Project.skills, " "),
            func.array_to_string(Project.achievements, " "),
        )
        rank = func.ts_rank_cd(
            func.to_tsvector("simple", project_text),
            func.plainto_tsquery("simple", query),
        ).label("rank")

        statement = (
            select(Project, rank)
            .where(Project.user_id == user_id)
            .order_by(rank.desc(), Project.id.asc())
            .limit(top_k)
        )
        result = await self._session.execute(statement)
        rows = result.all()
        ranked = [row[0] for row in rows if row[1] and row[1] > 0]
        if ranked:
            return ranked
        return (await self.get_by_user(user_id))[:top_k]

    async def delete(self, id: int, user_id: int) -> None:

        project = await self.get_by_id(id, user_id)
        if project is None:
            raise LookupError(f"Project {id} not found")
        await self._session.delete(project)
        await self._session.commit()

    async def delete_by_user(self, user_id: int) -> None:
        await self._session.execute(delete(Project).where(Project.user_id == user_id))

    def _create_project(self, dto: ProjectFromCVModel, user_id: int):

        normalized_tech: List[str] = [item.lower() for item in dto.technologies]

        return Project(
            name=dto.name,
            user_id=user_id,
            web_site=dto.website,
            skills=dto.skills,
            achievements=dto.achievements,
            company_name=dto.name,
            technologies=normalized_tech,
        )
