from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain import TemplateStatus
from app.models import (
    AutoParsedJob,
    CoverLetterTemplate,
    CoverLetterTemplateEdge,
    CoverLetterTemplateNode,
    LetterPhrase,
)
from app.repository.project_repository import ProjectRepository
from app.services.default_template_provisioner import DefaultTemplateProvisioner
from app.services.template_domain import (
    DomainProject,
    GraphEdge,
    GraphNode,
    RenderContext,
    classify_template_case,
    render_path,
    score_projects,
    select_path,
    validate_graph,
)


class TemplateConfigurationError(RuntimeError):
    def __init__(self, code: str, template_case: str | None = None):
        self.code = code
        self.template_case = template_case
        super().__init__(f"{code}: {template_case}" if template_case else code)


@dataclass(frozen=True)
class TemplateRenderResult:
    text: str
    detected_case: str
    template_case: str
    template_id: int
    template_version: int
    node_path: tuple[UUID, ...]


class TemplateGenerationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.projects = ProjectRepository(session)

    async def generate(self, vacancy: AutoParsedJob, user_id: int) -> str:
        result = await self.render(vacancy, user_id)
        vacancy.cover_letter_text = result.text
        vacancy.is_generated = True
        vacancy.cover_letter_template_id = result.template_id
        vacancy.cover_letter_template_case = result.detected_case
        vacancy.cover_letter_template_version = result.template_version
        vacancy.cover_letter_template_path = [
            str(node_id) for node_id in result.node_path
        ]
        self.session.add(vacancy)
        await self.session.commit()
        await self.session.refresh(vacancy)
        return result.text

    async def render(
        self,
        vacancy: AutoParsedJob,
        user_id: int,
        *,
        template_id: int | None = None,
    ) -> TemplateRenderResult:
        if vacancy.id is None:
            raise RuntimeError("Persisted vacancy is missing an id")
        await DefaultTemplateProvisioner(self.session).ensure_for_user(user_id)

        project_models = await self.projects.get_by_user(user_id)
        projects = [
            DomainProject(
                id=project.id,
                name=project.name,
                technologies=tuple(project.technologies or []),
            )
            for project in project_models
            if project.id is not None
        ]
        scored = score_projects(projects, f"{vacancy.job_title}\n{vacancy.job_text}")
        template_case = classify_template_case(scored)
        if template_id is None:
            template = await self.session.scalar(
                select(CoverLetterTemplate).where(
                    CoverLetterTemplate.user_id == user_id,
                    CoverLetterTemplate.template_case == template_case.value,
                    CoverLetterTemplate.status == TemplateStatus.ACTIVE.value,
                )
            )
        else:
            template = await self.session.scalar(
                select(CoverLetterTemplate).where(
                    CoverLetterTemplate.id == template_id,
                    CoverLetterTemplate.user_id == user_id,
                )
            )
        if template is None:
            raise TemplateConfigurationError(
                "active_template_not_found", template_case.value
            )
        if template.id is None or template.root_node_id is None:
            raise TemplateConfigurationError(
                "invalid_template_graph", template_case.value
            )

        nodes = list(
            (
                await self.session.scalars(
                    select(CoverLetterTemplateNode).where(
                        CoverLetterTemplateNode.template_id == template.id
                    )
                )
            ).all()
        )
        edges = list(
            (
                await self.session.scalars(
                    select(CoverLetterTemplateEdge).where(
                        CoverLetterTemplateEdge.template_id == template.id
                    )
                )
            ).all()
        )
        phrase_ids = {node.phrase_id for node in nodes if node.phrase_id is not None}
        phrases = {
            phrase.id: phrase
            for phrase in (
                await self.session.scalars(
                    select(LetterPhrase).where(LetterPhrase.id.in_(phrase_ids))
                )
            ).all()
        }
        domain_nodes = [
            GraphNode(
                id=node.id,
                node_kind=node.node_kind,
                phrase_id=node.phrase_id,
                phrase_text=(
                    phrases[node.phrase_id].text if node.phrase_id in phrases else None
                ),
                phrase_is_active=(
                    phrases[node.phrase_id].is_active
                    if node.phrase_id in phrases
                    else False
                ),
                phrase_is_owned=(
                    node.phrase_id in phrases
                    and phrases[node.phrase_id].user_id == user_id
                ),
            )
            for node in nodes
        ]
        domain_edges = [
            GraphEdge(
                edge.id,
                edge.source_node_id,
                edge.target_node_id,
                edge.branch_order,
            )
            for edge in edges
        ]
        validation = validate_graph(
            nodes=domain_nodes,
            edges=domain_edges,
            root_node_id=template.root_node_id,
            template_case=template_case,
            require_active_phrases=True,
        )
        if validation.errors:
            raise TemplateConfigurationError(
                "invalid_template_graph", template_case.value
            )

        path = select_path(
            vacancy_id=vacancy.id,
            template_id=template.id,
            template_version=template.version,
            root_node_id=template.root_node_id,
            edges=domain_edges,
        )
        if template_case.value == "no_relevant_projects":
            selected = [
                item.project
                for item in sorted(scored, key=lambda item: item.project.id)[:3]
            ]
        else:
            selected = [item.project for item in scored if item.match_count > 0][:3]
        matched = tuple(
            dict.fromkeys(
                technology
                for item in scored
                if item.match_count > 0
                for technology in item.matched_technologies
            )
        )
        letter = render_path(
            path=path,
            nodes={node.id: node for node in domain_nodes},
            context=RenderContext(
                job_title=vacancy.job_title,
                company_name=vacancy.company_name,
                matched_technologies=matched,
                projects=tuple(selected),
            ),
        )
        if not letter:
            raise TemplateConfigurationError(
                "empty_template_result", template_case.value
            )

        return TemplateRenderResult(
            text=letter,
            detected_case=template_case.value,
            template_case=(
                template.template_case.value
                if hasattr(template.template_case, "value")
                else str(template.template_case)
            ),
            template_id=template.id,
            template_version=template.version,
            node_path=tuple(path),
        )
