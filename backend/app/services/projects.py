from app.models import Project
from app.repository import ProjectRepository
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.schemas.llm_outputs.job_requirements import JobRequirement


class ProjectStorageService:
    def __init__(self, project_repository: ProjectRepository):
        self.repository = project_repository

    async def create_many(
        self,
        user_id: int,
        projects: list[ProjectFromCVModel],
    ):
        return await self.repository.create_many(user_id=user_id, projects=projects)

    async def delete(self, user_id: int, id: int):
        return await self.repository.delete(id, user_id)

    async def list_user_projects(self, user_id: int) -> list[dict]:
        projects = await self.repository.get_by_user(user_id)
        return [self._to_response(project) for project in projects]

    async def update_project(
        self,
        user_id: int,
        project_id: str,
        project: ProjectFromCVModel,
    ) -> dict:
        updated = await self.repository.update(int(project_id), user_id, project)
        if updated is None:
            raise LookupError(f"Project {project_id} not found")
        return self._to_response(updated)

    async def delete_project(self, user_id: int, project_id: str) -> bool:
        await self.repository.delete(int(project_id), user_id)
        return True

    async def rank_projects_overlap(
        self,
        user_id: int,
        vacancy: JobRequirement,
        top_k: int = 5,
        semantic_weight: float = 0.6,
        required_weight: float = 1.0,
        preferred_weight: float = 0.5,
        nice_to_have_weight: float = 0.2,
    ) -> list[dict]:
        query_text = self._build_vacancy_text(vacancy)
        projects = await self.repository.search_contexts(
            user_id=user_id,
            query=query_text,
            top_k=max(top_k * 3, top_k),
        )

        buckets = [
            (
                "required",
                [t.lower().strip() for t in vacancy.required_technologies],
                required_weight,
            ),
            (
                "preferred",
                [t.lower().strip() for t in vacancy.preferred_technologies],
                preferred_weight,
            ),
            (
                "nice_to_have",
                [t.lower().strip() for t in vacancy.nice_to_have_technologies],
                nice_to_have_weight,
            ),
        ]
        total_weight = sum(len(techs) * weight for _, techs, weight in buckets)
        text_terms = self._tokenize(query_text)

        candidates = []
        for project in projects:
            project_techs = {t.lower().strip() for t in project.technologies}
            matched_weight = 0.0
            matched = {"required": [], "preferred": [], "nice_to_have": []}

            for label, techs, weight in buckets:
                for tech in techs:
                    if tech in project_techs:
                        matched_weight += weight
                        matched[label].append(tech)

            weighted_overlap = (
                matched_weight / total_weight if total_weight > 0 else 0.0
            )
            text_score = self._text_score(project, text_terms)
            overlap_weight = 1.0 - semantic_weight
            final_score = (
                semantic_weight * text_score + overlap_weight * weighted_overlap
            )
            candidates.append(
                {
                    "semantic_score": round(text_score, 7),
                    "weighted_overlap": round(weighted_overlap, 4),
                    "score": round(final_score, 7),
                    "matched": matched,
                    "payload": self._to_response(project),
                }
            )

        candidates.sort(
            key=lambda x: (x["score"], len(x["matched"]["required"])),
            reverse=True,
        )
        return candidates[:top_k]

    @staticmethod
    def _to_response(project: Project) -> dict:
        return {
            "id": project.id,
            "source_id": project.id,
            "name": project.name,
            "website": project.web_site,
            "start_month": None,
            "start_year": None,
            "end_month": None,
            "end_year": None,
            "currently_working": False,
            "skills": project.skills or [],
            "achievements": project.achievements or [],
            "technologies": project.technologies or [],
        }

    @staticmethod
    def _build_vacancy_text(v: JobRequirement) -> str:
        lines = []
        if v.project_name:
            lines.append(v.project_name)

        all_techs = []
        all_techs.extend(v.required_technologies * 2)
        all_techs.extend(v.preferred_technologies)
        all_techs.extend(v.nice_to_have_technologies)

        if all_techs:
            lines.extend(all_techs)
        return " ".join(lines)

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token.strip(" ,.;:()[]{}<>/\\|-_").lower()
            for token in text.split()
            if len(token.strip(" ,.;:()[]{}<>/\\|-_")) > 1
        }

    @classmethod
    def _text_score(cls, project: Project, query_terms: set[str]) -> float:
        if not query_terms:
            return 0.0
        haystack = " ".join(
            [
                project.name or "",
                project.company_name or "",
                " ".join(project.technologies or []),
                " ".join(project.skills or []),
                " ".join(project.achievements or []),
            ]
        ).lower()
        matched = sum(1 for term in query_terms if term in haystack)
        return matched / len(query_terms)
