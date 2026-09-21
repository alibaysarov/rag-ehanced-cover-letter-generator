from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain import LetterPhraseType, TemplateCase, TemplateStatus
from app.helper import CurrentUser
from app.schemas.letter_constructor import (
    ActivateRequest,
    PhraseList,
    PhrasePatch,
    PhraseRead,
    PhraseWrite,
    Position,
    PreviewRequest,
    PreviewResponse,
    TemplateEdgeWrite,
    TemplateList,
    TemplateListItem,
    TemplateNodeRead,
    TemplateRead,
    TemplateWrite,
)
from app.services.letter_constructor import ConstructorError, LetterConstructorService

router = APIRouter()


def service(session: AsyncSession) -> LetterConstructorService:
    return LetterConstructorService(session)


def phrase_read(phrase, used: int) -> PhraseRead:
    return PhraseRead(
        id=phrase.id,
        type=phrase.type,
        text=phrase.text,
        is_active=phrase.is_active,
        used_in_templates=used,
        created_at=phrase.created_at,
        updated_at=phrase.updated_at,
    )


def constructor_error(error: ConstructorError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@router.get("/letter-phrases", response_model=PhraseList)
async def list_phrases(
    user: CurrentUser,
    q: str | None = None,
    phrase_type: LetterPhraseType | None = Query(default=None, alias="type"),
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await service(session).list_phrases(
        user.id, q, phrase_type, is_active, page, page_size
    )
    return PhraseList(
        items=[phrase_read(phrase, used) for phrase, used in rows],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/letter-phrases", response_model=PhraseRead, status_code=201)
async def create_phrase(
    user: CurrentUser,
    body: PhraseWrite,
    session: AsyncSession = Depends(get_db),
):
    try:
        phrase, used = await service(session).create_phrase(user.id, body)
        return phrase_read(phrase, used)
    except ConstructorError as error:
        return constructor_error(error)


@router.get("/letter-phrases/{phrase_id}", response_model=PhraseRead)
async def get_phrase(
    user: CurrentUser,
    phrase_id: int,
    session: AsyncSession = Depends(get_db),
):
    constructor = service(session)
    try:
        phrase = await constructor._phrase(phrase_id, user.id)
        used, _ = await constructor.phrase_usage(phrase_id)
        return phrase_read(phrase, used)
    except ConstructorError as error:
        return constructor_error(error)


@router.patch("/letter-phrases/{phrase_id}", response_model=PhraseRead)
async def update_phrase(
    user: CurrentUser,
    phrase_id: int,
    body: PhrasePatch,
    session: AsyncSession = Depends(get_db),
):
    try:
        phrase, used = await service(session).update_phrase(user.id, phrase_id, body)
        return phrase_read(phrase, used)
    except ConstructorError as error:
        return constructor_error(error)


@router.delete("/letter-phrases/{phrase_id}", status_code=204)
async def delete_phrase(
    user: CurrentUser,
    phrase_id: int,
    session: AsyncSession = Depends(get_db),
):
    try:
        await service(session).delete_phrase(user.id, phrase_id)
    except ConstructorError as error:
        return constructor_error(error)


async def template_read(
    constructor: LetterConstructorService, template
) -> TemplateRead:
    nodes, edges, phrases = await constructor.graph(template.id)
    phrase_usages = {
        phrase_id: (await constructor.phrase_usage(phrase_id))[0]
        for phrase_id in phrases
        if phrase_id is not None
    }
    return TemplateRead(
        id=template.id,
        name=template.name,
        case=template.template_case,
        status=template.status,
        root_node_id=template.root_node_id,
        version=template.version,
        nodes=[
            TemplateNodeRead(
                id=node.id,
                node_kind=node.node_kind,
                phrase_id=node.phrase_id,
                position=Position(x=node.position_x, y=node.position_y),
                phrase=(
                    phrase_read(phrases[node.phrase_id], phrase_usages[node.phrase_id])
                    if node.phrase_id in phrases
                    else None
                ),
            )
            for node in nodes
        ],
        edges=[
            TemplateEdgeWrite(
                id=edge.id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                branch_order=edge.branch_order,
            )
            for edge in edges
        ],
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get("/cover-letter-templates", response_model=TemplateList)
async def list_templates(
    user: CurrentUser,
    q: str | None = None,
    template_case: TemplateCase | None = Query(default=None, alias="case"),
    status: TemplateStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    rows, total = await service(session).list_templates(
        user.id, q, template_case, status, page, page_size
    )
    return TemplateList(
        items=[
            TemplateListItem(
                id=row[0].id,
                name=row[0].name,
                case=row[0].template_case,
                status=row[0].status,
                root_node_id=row[0].root_node_id,
                version=row[0].version,
                nodes_count=int(row[1]),
                edges_count=int(row[2]),
                has_projects_node=bool(row[3]),
                created_at=row[0].created_at,
                updated_at=row[0].updated_at,
            )
            for row in rows
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/cover-letter-templates", response_model=TemplateRead, status_code=201)
async def create_template(
    user: CurrentUser,
    body: TemplateWrite,
    session: AsyncSession = Depends(get_db),
):
    constructor = service(session)
    try:
        template = await constructor.save_template(user.id, body)
        return await template_read(constructor, template)
    except ConstructorError as error:
        return constructor_error(error)


@router.get("/cover-letter-templates/{template_id}", response_model=TemplateRead)
async def get_template(
    user: CurrentUser,
    template_id: int,
    session: AsyncSession = Depends(get_db),
):
    constructor = service(session)
    try:
        template = await constructor.get_template(template_id, user.id)
        return await template_read(constructor, template)
    except ConstructorError as error:
        return constructor_error(error)


@router.put("/cover-letter-templates/{template_id}", response_model=TemplateRead)
async def update_template(
    user: CurrentUser,
    template_id: int,
    body: TemplateWrite,
    session: AsyncSession = Depends(get_db),
):
    constructor = service(session)
    try:
        template = await constructor.save_template(user.id, body, template_id)
        return await template_read(constructor, template)
    except ConstructorError as error:
        return constructor_error(error)


@router.post(
    "/cover-letter-templates/{template_id}/activate", response_model=TemplateRead
)
async def activate_template(
    user: CurrentUser,
    template_id: int,
    body: ActivateRequest,
    session: AsyncSession = Depends(get_db),
):
    constructor = service(session)
    try:
        template = await constructor.activate(
            user.id, template_id, body.version, body.confirm_without_projects
        )
        return await template_read(constructor, template)
    except ConstructorError as error:
        return constructor_error(error)


@router.delete("/cover-letter-templates/{template_id}", status_code=204)
async def delete_template(
    user: CurrentUser,
    template_id: int,
    session: AsyncSession = Depends(get_db),
):
    try:
        await service(session).delete_template(user.id, template_id)
    except ConstructorError as error:
        return constructor_error(error)


@router.post(
    "/cover-letter-templates/{template_id}/preview", response_model=PreviewResponse
)
async def preview_template(
    user: CurrentUser,
    template_id: int,
    body: PreviewRequest,
    session: AsyncSession = Depends(get_db),
):
    try:
        result = await service(session).preview(user.id, template_id, body.vacancy_id)
        return PreviewResponse(
            detected_case=result.detected_case,
            template_case=result.template_case,
            text=result.text,
            node_path=list(result.node_path),
            warning=(
                "detected_case_mismatch"
                if result.detected_case != result.template_case
                else None
            ),
        )
    except ConstructorError as error:
        return constructor_error(error)
