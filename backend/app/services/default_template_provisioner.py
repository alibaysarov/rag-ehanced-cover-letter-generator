from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain import LetterPhraseType, TemplateCase, TemplateNodeKind, TemplateStatus
from app.models import (
    CoverLetterTemplate,
    CoverLetterTemplateEdge,
    CoverLetterTemplateNode,
    LetterPhrase,
    User,
)
from app.services.template_defaults import DEFAULT_TEMPLATE_SEEDS


class DefaultTemplateProvisioner:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_for_user(self, user_id: int) -> bool:
        user = await self.session.scalar(
            select(User).where(User.id == user_id).with_for_update()
        )
        if user is None:
            raise LookupError(f"User {user_id} does not exist")
        if user.defaults_provisioned_at is not None:
            return False

        existing = await self.session.scalar(
            select(CoverLetterTemplate.id)
            .where(CoverLetterTemplate.user_id == user_id)
            .limit(1)
        )
        if existing is not None:
            # Existing constructor data is user-owned and must never be overwritten.
            user.defaults_provisioned_at = datetime.now(timezone.utc)
            await self.session.commit()
            return False

        for case_value, seed in DEFAULT_TEMPLATE_SEEDS.items():
            template = CoverLetterTemplate(
                user_id=user_id,
                name=seed["name"],
                template_case=TemplateCase(case_value),
                status=TemplateStatus.DRAFT,
            )
            self.session.add(template)
            await self.session.flush()
            assert template.id is not None

            nodes: list[CoverLetterTemplateNode] = []
            for index, (kind_or_type, phrase_text) in enumerate(seed["blocks"]):
                phrase_id = None
                node_kind = TemplateNodeKind.PROJECTS
                if kind_or_type != "projects":
                    phrase = LetterPhrase(
                        user_id=user_id,
                        type=LetterPhraseType(kind_or_type),
                        text=phrase_text,
                        is_active=True,
                    )
                    self.session.add(phrase)
                    await self.session.flush()
                    phrase_id = phrase.id
                    node_kind = TemplateNodeKind.PHRASE
                nodes.append(
                    CoverLetterTemplateNode(
                        id=uuid4(),
                        template_id=template.id,
                        node_kind=node_kind,
                        phrase_id=phrase_id,
                        position_x=float(100 + index * 260),
                        position_y=160.0,
                    )
                )
            self.session.add_all(nodes)
            await self.session.flush()
            self.session.add_all(
                [
                    CoverLetterTemplateEdge(
                        id=uuid4(),
                        template_id=template.id,
                        source_node_id=source.id,
                        target_node_id=target.id,
                        branch_order=0,
                    )
                    for source, target in zip(nodes, nodes[1:])
                ]
            )
            template.root_node_id = nodes[0].id
            template.status = TemplateStatus.ACTIVE

        user.defaults_provisioned_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True
