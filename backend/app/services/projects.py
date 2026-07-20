from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.repository import ProjectRepository
from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.storage.repository.qdrant import QdrantStorage, get_projects_storage

from .embeddings import BaseEmbedder, LocalMistralEmbedder


class ProjectStorageService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        storage: QdrantStorage | None = None,
        embedder: BaseEmbedder | None = None,
    ):
        self.embedder = embedder or LocalMistralEmbedder()
        self.storage = storage or get_projects_storage(dim=self.embedder.dimensions)
        self.repository = project_repository

    async def create_many(
        self,
        user_id: int,
        projects: list[ProjectFromCVModel],
    ):

        created_count = await self.repository.create_many(
            user_id=user_id, projects=projects
        )
        return created_count

    async def delete(self, user_id: int, id: int):
        return await self.repository.delete(id, user_id)

    async def list_user_projects(self, user_id: int) -> list[dict]:
        projects = await self.repository.get_by_user(user_id)
        result = []
        for project in projects:
            result.append(
                {
                    "id": str(project.id),
                    "source_id": project.id,
                    "name": project.name,
                    "website": project.name,
                    "start_month": None,
                    "start_year": None,
                    "end_month": None,
                    "end_year": None,
                    "currently_working": False,
                    "skills": [],
                    "achievements": [],
                    "technologies": project.technologies,
                }
            )
        return result

    def update_project(
        self,
        user_id: int,
        project_id: str,
        project: ProjectFromCVModel,
    ) -> dict:
        existing = self.storage.get_point_by_id(project_id)
        if not existing or existing["payload"].get("user_id") != user_id:
            raise LookupError(f"Project {project_id} not found")

        source_id = existing["payload"].get("source_id", "")
        text = self._build_project_text(project)
        vector = self.embedder.embed_texts([text])[0]

        new_payload = {
            "user_id": user_id,
            "source_id": source_id,
            "project_name": project.name,
            "website": project.website,
            "start_month": project.start_month,
            "start_year": project.start_year,
            "end_month": project.end_month,
            "end_year": project.end_year,
            "currently_working": project.currently_working,
            "skills": project.skills,
            "achievements": project.achievements,
            "technologies": project.technologies,
            "tech_normalized": [t.lower().strip() for t in project.technologies],
            "text": text,
        }
        self.storage.upsert(ids=[project_id], vectors=[vector], payloads=[new_payload])
        return {
            "id": project_id,
            "source_id": source_id,
            "name": project.name,
            "website": project.website,
            "start_month": project.start_month,
            "start_year": project.start_year,
            "end_month": project.end_month,
            "end_year": project.end_year,
            "currently_working": project.currently_working,
            "skills": project.skills,
            "achievements": project.achievements,
            "technologies": project.technologies,
        }

    def delete_project(self, user_id: int, project_id: str) -> bool:
        existing = self.storage.get_point_by_id(project_id)
        if not existing or existing["payload"].get("user_id") != user_id:
            raise LookupError(f"Project {project_id} not found")
        self.storage.delete_by_point_id(project_id)
        return True

    def rank_projects_overlap(
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
        query_vector = self.embedder.embed_query(query_text)

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
        total_weight = sum(len(techs) * w for _, techs, w in buckets)

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        )

        found = self._search(
            query_vector=query_vector,
            top_k=top_k * 3,
            query_filter=query_filter,
        )

        overlap_weight = 1.0 - semantic_weight
        candidates = []
        for payload, score in zip(found["sources"], found.get("scores", [])):
            project_techs = set(payload.get("tech_normalized", []))

            matched_weight = 0.0
            matched = {"required": [], "preferred": [], "nice_to_have": []}
            for label, techs, w in buckets:
                for t in techs:
                    if t in project_techs:
                        matched_weight += w
                        matched[label].append(t)

            weighted_overlap = (
                matched_weight / total_weight if total_weight > 0 else 0.0
            )
            final_score = semantic_weight * score + overlap_weight * weighted_overlap
            candidates.append(
                {
                    "semantic_score": round(score, 7),
                    "weighted_overlap": round(weighted_overlap, 4),
                    "score": round(final_score, 7),
                    "matched": matched,
                    "payload": payload,
                }
            )

        candidates.sort(
            key=lambda x: (x["score"], len(x["matched"]["required"])),
            reverse=True,
        )
        return candidates[:top_k]

    def _search(self, query_vector: list[float], top_k: int, query_filter: Filter):
        return self.storage.search(
            query_vector=query_vector, top_k=top_k, query_filter=query_filter
        )

    @staticmethod
    def _build_project_text(p: ProjectFromCVModel) -> str:
        lines = [f"Проект: {p.name}"]
        if p.skills:
            lines.append(f"Навыки: {', '.join(p.skills)}")
        if p.achievements:
            lines.append("Достижения:")
            lines.extend(f"- {a}" for a in p.achievements)
        if p.technologies:
            lines.append(f"Технологии: {', '.join(p.technologies)}")
        return "\n".join(lines)

    @staticmethod
    def _build_vacancy_text(v: JobRequirement) -> str:
        lines = [""]
        if v.project_name:
            lines.append(f"Область проекта: {v.project_name}")

        all_techs = []
        all_techs.extend(v.required_technologies * 2)
        all_techs.extend(v.preferred_technologies)
        all_techs.extend(v.nice_to_have_technologies)

        if all_techs:
            lines.append("Технологии:")
            lines.extend(f"- {t}" for t in all_techs)
        return "\n".join(lines)
