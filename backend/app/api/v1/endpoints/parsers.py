from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError

from app.cache.redis import async_client
from app.dependencies import DBSession
from app.helper import CurrentUser
from app.repository.parser_repository import ParserRepository
from app.schemas.parser import (
    ParserCreate,
    ParserDetail,
    ParserList,
    ParserListItem,
    ParserUpdate,
)
from app.schemas.parser_preview import PreviewRequest, PreviewResponse
from app.services.parser_catalog import ParserCatalogService
from app.services.parser_preview import run_preview

router = APIRouter()


@router.post("/preview", response_model=PreviewResponse)
async def preview_parser(payload: PreviewRequest, user: CurrentUser):
    try:
        return await run_preview(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "preview_validation", "message": str(exc)}
        ) from exc
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={"code": "preview_timeout", "message": "Preview timed out"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "preview_failed", "message": str(exc)[:200]},
        ) from exc


def error_detail(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


@router.get("", response_model=ParserList)
async def list_parsers(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    repository = ParserRepository(db)
    items, total = await repository.list_page(user.id, page, page_size)
    ids = [item.id for item in items if item.id is not None]
    busy = await repository.in_use_ids(ids)
    return ParserList(
        items=[
            ParserListItem.model_validate(
                {
                    **item.model_dump(),
                    "is_in_use": item.id in busy,
                    "can_delete": item.id not in busy,
                }
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{parser_id}", response_model=ParserDetail)
async def get_parser(parser_id: int, user: CurrentUser, db: DBSession):
    repository = ParserRepository(db)
    parser = await repository.get_owned(parser_id, user.id)
    if parser is None:
        raise HTTPException(status_code=404, detail="Parser not found")
    in_use = await repository.is_in_use(parser_id)
    return ParserDetail.model_validate(
        {**parser.model_dump(), "is_in_use": in_use, "can_delete": not in_use}
    )


@router.post("", response_model=ParserDetail, status_code=status.HTTP_201_CREATED)
async def create_parser(payload: ParserCreate, user: CurrentUser, db: DBSession):
    repository = ParserRepository(db)
    try:
        parser, old_revision = await repository.create(user.id, payload)
        await db.commit()
        await db.refresh(parser)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=error_detail(
                "parser_domain_exists", "Сайт с таким доменом уже существует"
            ),
        ) from exc
    await ParserCatalogService(db, async_client).invalidate(user.id, old_revision)
    return ParserDetail.model_validate(
        {**parser.model_dump(), "is_in_use": False, "can_delete": True}
    )


@router.put("/{parser_id}", response_model=ParserDetail)
async def update_parser(
    parser_id: int, payload: ParserUpdate, user: CurrentUser, db: DBSession
):
    repository = ParserRepository(db)
    try:
        parser, old_revision, conflict = await repository.update(
            parser_id, user.id, payload
        )
        if parser is None:
            await db.rollback()
            raise HTTPException(status_code=404, detail="Parser not found")
        if conflict:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=error_detail(
                    "parser_version_conflict",
                    "Настройки уже изменены. Загрузите актуальную версию.",
                ),
            )
        await db.commit()
        await db.refresh(parser)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=error_detail(
                "parser_domain_exists", "Сайт с таким доменом уже существует"
            ),
        ) from exc
    await ParserCatalogService(db, async_client).invalidate(user.id, old_revision)
    in_use = await repository.is_in_use(parser_id)
    return ParserDetail.model_validate(
        {**parser.model_dump(), "is_in_use": in_use, "can_delete": not in_use}
    )


@router.delete("/{parser_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parser(parser_id: int, user: CurrentUser, db: DBSession):
    repository = ParserRepository(db)
    found, old_revision, in_use = await repository.delete(parser_id, user.id)
    if not found:
        await db.rollback()
        raise HTTPException(status_code=404, detail="Parser not found")
    if in_use:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=error_detail(
                "parser_in_use",
                "Сайт сейчас используется для парсинга. Удаление станет доступно после завершения",
            ),
        )
    await db.commit()
    await ParserCatalogService(db, async_client).invalidate(user.id, old_revision)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
