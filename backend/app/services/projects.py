import uuid
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.schemas.llm_outputs.cv_parse import ProjectFromCVModel
from app.schemas.llm_outputs.job_requirements import JobRequirement
from app.services.embeddings import BaseEmbedder, OpenAIEmbedder,LocalMistralEmbedder
from app.storage.repository.qdrant import QdrantStorage, get_projects_storage


_PROJECT_NAMESPACE = uuid.NAMESPACE_DNS


class ProjectStorageService:
    def __init__(
        self,
        storage: QdrantStorage | None = None,
        embedder: BaseEmbedder | None = None,
    ):
        self.embedder = embedder or LocalMistralEmbedder()
        self.storage = storage or get_projects_storage(dim=self.embedder.dimensions)

    def save_projects(
        self,
        user_id: int,
        source_id: str,
        projects: list[ProjectFromCVModel],
    ) -> int:
        if not projects:
            self.storage.delete_by_source_id(source_id)
            return 0

        texts = [self._build_project_text(p) for p in projects]
        vectors = self.embedder.embed_texts(texts)

        ids = [
            str(uuid.uuid5(_PROJECT_NAMESPACE, f"{user_id}:{source_id}:{p.name}"))
            for p in projects
        ]
        payloads = [
            {
                "user_id": user_id,
                "source_id": source_id,
                "project_name": p.name,
                "skills": p.skills,
                "achievements": p.achievements,
                "technologies": p.technologies,
                "tech_normalized": [t.lower().strip() for t in p.technologies],
                "text": texts[i],
            }
            for i, p in enumerate(projects)
        ]

        self.storage.delete_by_source_id(source_id)
        self.storage.upsert(ids=ids, vectors=vectors, payloads=payloads)
        return len(projects)

    def list_user_projects(self, user_id: int) -> list[dict]:
        points = self.storage.list_by_user_id(user_id)
        result = []
        for p in points:
            payload = p["payload"]
            result.append({
                "id": p["id"],
                "source_id": payload.get("source_id", ""),
                "name": payload.get("project_name", ""),
                "skills": payload.get("skills", []),
                "achievements": payload.get("achievements", []),
                "technologies": payload.get("technologies", []),
            })
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

    def rank_projects(
        self,
        user_id: int,
        vacancy: JobRequirement,
        top_k: int = 5,
    ) -> list[dict]:
        query_text = self._build_vacancy_text(vacancy)
        query_vector = self.embedder.embed_query(query_text)

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        )

        found = self.storage.search(
            query_vector=query_vector,
            top_k=top_k,
            query_filter=query_filter,
        )

        ranked = []
        for payload, score in zip(found["sources"], found.get("scores", [])):
            ranked.append({"score": score, "payload": payload})
        return ranked

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
        lines = [f"Должность: {v.name}"]
        if v.project_name:
            lines.append(f"Область проекта: {v.project_name}")
        if v.requirements:
            lines.append("Требования:")
            lines.extend(f"- {r}" for r in v.requirements)
        return "\n".join(lines)


_projects_service: ProjectStorageService | None = None


def get_projects_service() -> ProjectStorageService:
    global _projects_service
    if _projects_service is None:
        _projects_service = ProjectStorageService()
    return _projects_service
