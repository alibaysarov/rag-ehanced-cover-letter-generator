from __future__ import annotations

from datetime import datetime, timezone
from typing import NoReturn

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select, update

from app.domain import LetterPhraseType, TemplateCase, TemplateNodeKind, TemplateStatus
from app.models import (
    AutoParsedJob,
    CoverLetterTemplate,
    CoverLetterTemplateEdge,
    CoverLetterTemplateNode,
    LetterPhrase,
)
from app.schemas.letter_constructor import PhrasePatch, PhraseWrite, TemplateWrite
from app.services.template_domain import (
    GraphEdge,
    GraphNode,
    unknown_tokens,
    validate_graph,
)


class ConstructorError(Exception):
    def __init__(self, status_code: int, detail: dict[str, object]):
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def fail(status: int, code: str, **detail: object) -> NoReturn:
    raise ConstructorError(status, {"code": code, **detail})


class LetterConstructorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _phrase(self, phrase_id: int, user_id: int) -> LetterPhrase:
        phrase = await self.session.scalar(
            select(LetterPhrase).where(
                LetterPhrase.id == phrase_id, LetterPhrase.user_id == user_id
            )
        )
        if phrase is None:
            fail(404, "phrase_not_found")
        return phrase

    async def phrase_usage(self, phrase_id: int) -> tuple[int, list[int]]:
        rows = (
            (
                await self.session.execute(
                    select(CoverLetterTemplateNode.template_id)
                    .where(CoverLetterTemplateNode.phrase_id == phrase_id)
                    .distinct()
                    .order_by(CoverLetterTemplateNode.template_id)
                )
            )
            .scalars()
            .all()
        )
        return len(rows), list(rows)

    async def list_phrases(
        self,
        user_id: int,
        q: str | None,
        phrase_type: LetterPhraseType | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[LetterPhrase, int]], int]:
        usage = (
            select(
                CoverLetterTemplateNode.phrase_id.label("phrase_id"),
                func.count(func.distinct(CoverLetterTemplateNode.template_id)).label(
                    "used"
                ),
            )
            .where(CoverLetterTemplateNode.phrase_id.is_not(None))
            .group_by(CoverLetterTemplateNode.phrase_id)
            .subquery()
        )
        conditions = [LetterPhrase.user_id == user_id]
        if q:
            conditions.append(LetterPhrase.text.ilike(f"%{q}%"))
        if phrase_type:
            conditions.append(LetterPhrase.type == phrase_type.value)
        if is_active is not None:
            conditions.append(LetterPhrase.is_active == is_active)
        total = await self.session.scalar(
            select(func.count()).select_from(LetterPhrase).where(*conditions)
        )
        rows = (
            await self.session.execute(
                select(LetterPhrase, func.coalesce(usage.c.used, 0))
                .outerjoin(usage, usage.c.phrase_id == LetterPhrase.id)
                .where(*conditions)
                .order_by(LetterPhrase.updated_at.desc(), LetterPhrase.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return [(row[0], int(row[1])) for row in rows], int(total or 0)

    def _validate_phrase(self, text: str) -> str:
        clean = text.strip()
        invalid = sorted(unknown_tokens(clean))
        if not clean or len(clean) > 2000 or invalid:
            fail(422, "invalid_phrase", unknown_tokens=invalid)
        return clean

    async def create_phrase(
        self, user_id: int, body: PhraseWrite
    ) -> tuple[LetterPhrase, int]:
        phrase = LetterPhrase(
            user_id=user_id,
            type=body.type,
            text=self._validate_phrase(body.text),
            is_active=body.is_active,
        )
        self.session.add(phrase)
        await self.session.commit()
        await self.session.refresh(phrase)
        return phrase, 0

    async def update_phrase(
        self, user_id: int, phrase_id: int, body: PhrasePatch
    ) -> tuple[LetterPhrase, int]:
        phrase = await self._phrase(phrase_id, user_id)
        used, template_ids = await self.phrase_usage(phrase_id)
        if body.is_active is False and phrase.is_active:
            active_usage = await self.session.scalar(
                select(func.count())
                .select_from(CoverLetterTemplateNode)
                .join(CoverLetterTemplate)
                .where(
                    CoverLetterTemplateNode.phrase_id == phrase_id,
                    CoverLetterTemplate.status == TemplateStatus.ACTIVE.value,
                )
            )
            if active_usage:
                fail(409, "active_template_would_be_invalid", template_ids=template_ids)
        if body.text is not None:
            phrase.text = self._validate_phrase(body.text)
        if body.type is not None:
            phrase.type = body.type
        if body.is_active is not None:
            phrase.is_active = body.is_active
        phrase.updated_at = datetime.now(timezone.utc)
        if used and body.text is not None:
            await self.session.execute(
                update(CoverLetterTemplate)
                .where(CoverLetterTemplate.id.in_(template_ids))
                .values(
                    version=CoverLetterTemplate.version + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        await self.session.commit()
        await self.session.refresh(phrase)
        return phrase, used

    async def delete_phrase(self, user_id: int, phrase_id: int) -> None:
        phrase = await self._phrase(phrase_id, user_id)
        used, template_ids = await self.phrase_usage(phrase_id)
        if used:
            fail(409, "phrase_in_use", template_ids=template_ids)
        await self.session.delete(phrase)
        await self.session.commit()

    async def _template(self, template_id: int, user_id: int) -> CoverLetterTemplate:
        template = await self.session.scalar(
            select(CoverLetterTemplate).where(
                CoverLetterTemplate.id == template_id,
                CoverLetterTemplate.user_id == user_id,
            )
        )
        if template is None:
            fail(404, "template_not_found")
        return template

    async def get_template(self, template_id: int, user_id: int) -> CoverLetterTemplate:
        return await self._template(template_id, user_id)

    async def list_templates(
        self,
        user_id: int,
        q: str | None,
        template_case: TemplateCase | None,
        status: TemplateStatus | None,
        page: int,
        page_size: int,
    ):
        node_counts = (
            select(
                CoverLetterTemplateNode.template_id.label("template_id"),
                func.count().label("nodes_count"),
                func.bool_or(
                    CoverLetterTemplateNode.node_kind == TemplateNodeKind.PROJECTS.value
                ).label("has_projects_node"),
            )
            .group_by(CoverLetterTemplateNode.template_id)
            .subquery()
        )
        edge_counts = (
            select(
                CoverLetterTemplateEdge.template_id.label("template_id"),
                func.count().label("edges_count"),
            )
            .group_by(CoverLetterTemplateEdge.template_id)
            .subquery()
        )
        conditions = [CoverLetterTemplate.user_id == user_id]
        if q:
            conditions.append(CoverLetterTemplate.name.ilike(f"%{q}%"))
        if template_case:
            conditions.append(CoverLetterTemplate.template_case == template_case.value)
        if status:
            conditions.append(CoverLetterTemplate.status == status.value)
        total = await self.session.scalar(
            select(func.count()).select_from(CoverLetterTemplate).where(*conditions)
        )
        rows = (
            await self.session.execute(
                select(
                    CoverLetterTemplate,
                    func.coalesce(node_counts.c.nodes_count, 0),
                    func.coalesce(edge_counts.c.edges_count, 0),
                    func.coalesce(node_counts.c.has_projects_node, False),
                )
                .outerjoin(
                    node_counts, node_counts.c.template_id == CoverLetterTemplate.id
                )
                .outerjoin(
                    edge_counts, edge_counts.c.template_id == CoverLetterTemplate.id
                )
                .where(*conditions)
                .order_by(
                    CoverLetterTemplate.updated_at.desc(),
                    CoverLetterTemplate.id.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return rows, int(total or 0)

    async def graph(self, template_id: int):
        nodes = list(
            (
                await self.session.scalars(
                    select(CoverLetterTemplateNode).where(
                        CoverLetterTemplateNode.template_id == template_id
                    )
                )
            ).all()
        )
        edges = list(
            (
                await self.session.scalars(
                    select(CoverLetterTemplateEdge).where(
                        CoverLetterTemplateEdge.template_id == template_id
                    )
                )
            ).all()
        )
        phrase_ids = {n.phrase_id for n in nodes if n.phrase_id is not None}
        phrases = {}
        if phrase_ids:
            phrases = {
                p.id: p
                for p in (
                    await self.session.scalars(
                        select(LetterPhrase).where(LetterPhrase.id.in_(phrase_ids))
                    )
                ).all()
            }
        return nodes, edges, phrases

    async def _validate_graph(
        self,
        user_id: int,
        template_case: TemplateCase,
        root_node_id,
        node_data,
        edge_data,
        confirm: bool,
        active: bool,
        full: bool,
    ) -> None:
        phrase_ids = {n.phrase_id for n in node_data if n.phrase_id is not None}
        phrases = {}
        if phrase_ids:
            phrases = {
                p.id: p
                for p in (
                    await self.session.scalars(
                        select(LetterPhrase).where(LetterPhrase.id.in_(phrase_ids))
                    )
                ).all()
            }
        nodes = [
            GraphNode(
                n.id,
                n.node_kind,
                n.phrase_id,
                phrases[n.phrase_id].text if n.phrase_id in phrases else None,
                phrases[n.phrase_id].is_active if n.phrase_id in phrases else False,
                n.phrase_id in phrases and phrases[n.phrase_id].user_id == user_id,
            )
            for n in node_data
        ]
        edges = [
            GraphEdge(e.id, e.source_node_id, e.target_node_id, e.branch_order)
            for e in edge_data
        ]
        result = validate_graph(
            nodes=nodes,
            edges=edges,
            root_node_id=root_node_id,
            template_case=template_case,
            require_active_phrases=active,
        )
        errors = list(result.errors)
        if not full:
            basic_codes = {
                "duplicate_node_id",
                "duplicate_edge_id",
                "node_limit_exceeded",
                "edge_limit_exceeded",
                "duplicate_projects_node",
                "projects_node_forbidden",
                "invalid_node_phrase",
                "foreign_phrase",
                "dangling_edge",
                "self_loop",
                "duplicate_edge",
                "duplicate_branch_order",
                "invalid_branch_order",
            }
            errors = [error for error in errors if error["code"] in basic_codes]
        if errors:
            fail(422, "invalid_template_graph", errors=errors)
        if (
            template_case != TemplateCase.NO_PORTFOLIO
            and result.paths_without_projects
            and not confirm
        ):
            reason = (
                "missing_projects_node"
                if not any(n.node_kind == TemplateNodeKind.PROJECTS for n in nodes)
                else "projects_node_not_on_all_paths"
            )
            fail(422, "projects_node_confirmation_required", reason=reason)

    async def save_template(
        self, user_id: int, body: TemplateWrite, template_id: int | None = None
    ) -> CoverLetterTemplate:
        is_active_edit = False
        if template_id is None:
            if body.version is not None:
                fail(422, "invalid_template_version")
            template = CoverLetterTemplate(
                user_id=user_id,
                name=body.name.strip(),
                template_case=body.template_case,
                status=TemplateStatus.DRAFT,
            )
            self.session.add(template)
            await self.session.flush()
        else:
            template = await self._template(template_id, user_id)
            if body.version is None or body.version != template.version:
                fail(409, "stale_template_version", current_version=template.version)
            previous_status = template.status
            is_active_edit = previous_status == TemplateStatus.ACTIVE
            if previous_status == TemplateStatus.ACTIVE:
                template.status = TemplateStatus.DRAFT
            template.root_node_id = None
            await self.session.flush()
            await self.session.execute(
                delete(CoverLetterTemplateEdge).where(
                    CoverLetterTemplateEdge.template_id == template.id
                )
            )
            await self.session.execute(
                delete(CoverLetterTemplateNode).where(
                    CoverLetterTemplateNode.template_id == template.id
                )
            )
            template.version += 1
        assert template.id is not None
        await self._validate_graph(
            user_id,
            body.template_case,
            body.root_node_id,
            body.nodes,
            body.edges,
            body.confirm_without_projects,
            is_active_edit,
            is_active_edit,
        )
        template.name = body.name.strip()
        template.template_case = body.template_case
        template.updated_at = datetime.now(timezone.utc)
        self.session.add_all(
            [
                CoverLetterTemplateNode(
                    id=n.id,
                    template_id=template.id,
                    node_kind=n.node_kind,
                    phrase_id=n.phrase_id,
                    position_x=n.position.x,
                    position_y=n.position.y,
                )
                for n in body.nodes
            ]
        )
        await self.session.flush()
        self.session.add_all(
            [
                CoverLetterTemplateEdge(
                    id=e.id,
                    template_id=template.id,
                    source_node_id=e.source_node_id,
                    target_node_id=e.target_node_id,
                    branch_order=e.branch_order,
                )
                for e in body.edges
            ]
        )
        template.root_node_id = body.root_node_id
        if template_id is not None:
            template.status = previous_status
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def activate(
        self, user_id: int, template_id: int, version: int, confirm: bool
    ):
        template = await self._template(template_id, user_id)
        if version != template.version:
            fail(409, "stale_template_version", current_version=template.version)
        nodes, edges, phrases = await self.graph(template.id)
        await self._validate_graph(
            user_id,
            template.template_case,
            template.root_node_id,
            nodes,
            edges,
            confirm,
            True,
            True,
        )
        await self.session.execute(
            update(CoverLetterTemplate)
            .where(
                CoverLetterTemplate.user_id == user_id,
                CoverLetterTemplate.template_case == template.template_case,
                CoverLetterTemplate.status == TemplateStatus.ACTIVE.value,
                CoverLetterTemplate.id != template.id,
            )
            .values(status=TemplateStatus.ARCHIVED.value)
        )
        template.status = TemplateStatus.ACTIVE
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete_template(self, user_id: int, template_id: int) -> None:
        template = await self._template(template_id, user_id)
        if template.status == TemplateStatus.ACTIVE:
            fail(409, "active_template")
        await self.session.delete(template)
        await self.session.commit()

    async def preview(self, user_id: int, template_id: int, vacancy_id: int):
        await self._template(template_id, user_id)
        vacancy = await self.session.scalar(
            select(AutoParsedJob).where(
                AutoParsedJob.id == vacancy_id, AutoParsedJob.user_id == user_id
            )
        )
        if vacancy is None:
            fail(404, "vacancy_not_found")
        from app.services.template_generation import (
            TemplateConfigurationError,
            TemplateGenerationService,
        )

        try:
            return await TemplateGenerationService(self.session).render(
                vacancy, user_id, template_id=template_id
            )
        except TemplateConfigurationError as error:
            fail(422, error.code, template_case=error.template_case)
