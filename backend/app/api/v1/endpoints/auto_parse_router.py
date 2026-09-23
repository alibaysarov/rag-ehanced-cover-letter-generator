import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlmodel import desc, select
from starlette.concurrency import run_in_threadpool

from app.cache.redis import async_client
from app.commands import GenerateLetterCommand, build_handler
from app.database import async_session_maker
from app.dependencies import (
    DBSession,
    get_auto_parse_repository,
    get_sent_letter_repository,
    get_websocket_manager,
)
from app.helper import CurrentUser, WsUser
from app.models.auto_parsed_job import AutoParsedJob
from app.models.parsing_job import ParsingJob
from app.repository.auto_parse_job_repository import AutoParseJobRepository
from app.repository.parsing_job_repository import ParsingJobRepository
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository
from app.schemas.api.auto_parse import (
    AutoParsedJobRead,
    MarkAppliedRequest,
    StartParseRequest,
)
from app.schemas.generation_mode import GenerationMode
from app.services.auto_generate import start_batch, start_test_batch, stream_gen_events
from app.services.websocket.websocket_manager import WebSocketManager
from app.tasks.parse_site import parse_site

logger = logging.getLogger(__name__)
router = APIRouter()

# ws_manager = get_websocket_manager()


@router.post("/test-send")
async def test_send(
    user: CurrentUser,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
    auto_parse_job_repo: AutoParseJobRepository = Depends(get_auto_parse_repository),
):
    #   await ws_manager.send_text(user.id,"Example text")
    job_id = 54
    vacancies = await auto_parse_job_repo.get_by_job_id(job_id)
    vacancy_ids: list[int] = [
        item.id for item in vacancies[0:10] if item.id is not None
    ]
    start_test_batch(user.id, job_id, vacancy_ids)
    # start_batch()
    return {"Message": "123"}


@router.websocket("/ws")
async def ws_connect(
    user: WsUser,
    websocket: WebSocket,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
):
    await ws_manager.connect(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # обработка входящих сообщений
            print("Data from ws", data)
            await ws_manager.send_text(user.id, f"echo: {data}")
    except WebSocketDisconnect:
        await ws_manager.disconnect(user.id, websocket)
    except Exception as e:
        logger.exception("Ошибка в WS-соединении user_id=%s", user.id)
        await ws_manager.disconnect(user.id, websocket)


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
async def start_parse_test(
    user: CurrentUser,
    body: StartParseRequest,
):
    repository = ParsingJobRepository(async_session_maker)
    try:
        parsing_job, site_jobs = await repository.create_job_with_parsers(
            user.id,
            body.query,
            body.generation_mode,
            vacancy_limit=body.vacancy_limit,
            parser_ids=body.parser_ids,
        )
    except ValueError as exc:
        if str(exc) == "parsers_empty":
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "parsers_empty",
                    "message": "Добавьте хотя бы один сайт для поиска",
                    "href": "/search-sites",
                },
            ) from exc
        raise
    if parsing_job.id is None:
        logger.error("failed to create parsing job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Возникла ошибка попробуйте позже",
        )

    try:
        for site_job in site_jobs:
            if site_job.id is None:
                raise RuntimeError("Parsing site job was not assigned an id")
            await run_in_threadpool(parse_site.apply_async, args=(site_job.id,))
    except Exception:
        logger.exception("Could not dispatch parsing job %s", parsing_job.id)
        await repository.fail_pending_dispatch(parsing_job.id, "dispatch failure")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Не удалось запустить все парсеры",
                "parsing_job_id": parsing_job.id,
            },
        )

    return {"parsing_job_id": parsing_job.id}


@router.get("/status/{parsing_job_id}")
async def get_status(
    user: CurrentUser,
    parsing_job_id: int,
    request: Request,
    db: DBSession,
):
    job = await db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")
    return job


@router.get("/jobs/{parsing_job_id}/vacancies", response_model=list[AutoParsedJobRead])
async def get_vacancies(
    user: CurrentUser,
    parsing_job_id: int,
    db: DBSession,
):
    job = await db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    result = await db.execute(
        select(AutoParsedJob)
        .where(AutoParsedJob.parsing_job_id == parsing_job_id)
        .order_by(AutoParsedJob.id)
    )
    vacancies = result.scalars().all()
    print("List \n", vacancies)
    return [AutoParsedJobRead.model_validate(vacancy) for vacancy in vacancies]


@router.patch("/vacancies/{vacancy_id}/applied")
async def mark_applied(
    user: CurrentUser,
    vacancy_id: int,
    body: MarkAppliedRequest,
    request: Request,
    db: DBSession,
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):
    vacancy = await db.get(AutoParsedJob, vacancy_id)
    if not vacancy or vacancy.user_id != user.id:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    vacancy.is_applied = True
    db.add(vacancy)

    await repo.create(
        user_id=user.id,
        url=vacancy.url,
        job_name=vacancy.job_title,
        letter_text=body.letter_text or vacancy.job_title,
    )

    await db.commit()
    await db.refresh(vacancy)
    return vacancy


@router.patch("/vacancies/{vacancy_id}/viewed")
async def mark_viewed(
    user: CurrentUser,
    vacancy_id: int,
    db: DBSession,
):
    vacancy = await db.get(AutoParsedJob, vacancy_id)
    if not vacancy or vacancy.user_id != user.id:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    if not vacancy.is_viewed:
        vacancy.is_viewed = True
        db.add(vacancy)
        await db.commit()
        await db.refresh(vacancy)
    return vacancy


@router.post("/vacancies/{vacancy_id}/generate-stream")
async def generate_vacancy_stream(vacancy_id: int, user: CurrentUser, db: DBSession):
    """Generate against the persisted vacancy, so its parent's mode is authoritative."""
    vacancy = await db.get(AutoParsedJob, vacancy_id)
    if not vacancy or vacancy.user_id != user.id or vacancy.parsing_job_id is None:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    parent = await db.get(ParsingJob, vacancy.parsing_job_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Parsing job not found")
    meta_total = await async_client.hget(f"batch_meta:{parent.id}", "total")
    statuses = await async_client.hgetall(f"batch:{parent.id}") or {}
    terminal = {"generated", "failed", "not_found"}
    if meta_total and sum(
        json.loads(value)["status"] in terminal for value in statuses.values()
    ) < int(meta_total):
        raise HTTPException(status_code=409, detail="Batch generation is running")

    async def events() -> AsyncIterator[str]:
        try:
            letter = await build_handler(db).handle(
                GenerateLetterCommand(
                    vacancy_id=vacancy_id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    generation_mode=parent.generation_mode,
                )
            )
            yield f"data: {json.dumps({'delta': letter}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("Single vacancy generation failed")
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@router.get("/history")
async def get_history(
    user: CurrentUser,
    db: DBSession,
):
    result = await db.execute(
        select(ParsingJob)
        .where(ParsingJob.user_id == user.id)
        .order_by(desc(ParsingJob.id))
    )
    return result.scalars().all()


@router.post("/jobs/{parsing_job_id}/generate")
async def start_test_generation(
    parsing_job_id: int,
    user: CurrentUser,
    db: DBSession,
    auto_parse_job_repo: AutoParseJobRepository = Depends(get_auto_parse_repository),
):
    job = await db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail="Parsing job is not done yet")

    active_total = await async_client.hget(f"batch_meta:{parsing_job_id}", "total")
    active_statuses = await async_client.hgetall(f"batch:{parsing_job_id}") or {}
    terminal_statuses = {"generated", "failed", "not_found"}
    if active_total:
        completed = sum(
            json.loads(value)["status"] in terminal_statuses
            for value in active_statuses.values()
        )
        if completed < int(active_total):
            raise HTTPException(status_code=409, detail="Generation is already running")

    try:
        vacancies = await auto_parse_job_repo.get_by_job_id(parsing_job_id)
        vacancy_ids: list[int] = [item.id for item in vacancies if item.id is not None]
        start_batch(
            user.id,
            parsing_job_id,
            vacancy_ids,
            user.first_name,
            user.last_name,
            job.generation_mode.value,
        )
        return {
            "status": "started",
        }
    except Exception as e:
        logger.error("An error during auto generation %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Возникла ошибка попробуйте позже",
        )


@router.get("/jobs/{parsing_job_id}/generate-status")
async def get_generate_status(
    parsing_job_id: int,
    user: CurrentUser,
    db: DBSession,
):
    job = await db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    result = await db.execute(
        select(AutoParsedJob).where(AutoParsedJob.parsing_job_id == parsing_job_id)
    )
    vacancies = result.scalars().all()

    total = len(vacancies)
    generated = sum(1 for v in vacancies if v.is_generated)

    # статусы из Redis по конкретным vacancy_id этой job
    raw_statuses = await async_client.hgetall(f"batch:{parsing_job_id}") or {}
    print("raw statuses", raw_statuses)
    statuses: dict[str, dict] = {
        k.decode() if isinstance(k, bytes) else k: json.loads(v)
        for k, v in raw_statuses.items()
    }

    terminal = {"generated", "failed", "not_found"}
    finished_count = sum(1 for s in statuses.values() if s["status"] in terminal)
    failed_count = sum(1 for s in statuses.values() if s["status"] == "failed")

    batch_total_raw = await async_client.hget(f"batch_meta:{parsing_job_id}", "total")
    batch_total = int(batch_total_raw) if batch_total_raw else 0

    # батч считается активным, если для него есть метаданные и не все таски отработали
    is_running = batch_total > 0 and finished_count < batch_total

    return {
        "is_running": is_running,
        "generated": generated,
        "failed": failed_count,
        "total": total,
        "statuses": statuses,  # опционально: детальный статус по каждой вакансии
        "auto_generation_status": (
            "not_applicable"
            if job.generation_mode == GenerationMode.AI
            else "failed"
            if job.auto_generation_error
            else "started"
            if job.auto_generation_started_at
            else "waiting_for_parse"
            if job.status in {"pending", "running"}
            else "skipped"
            if job.status != "done" or total == 0
            else "pending"
        ),
        "auto_generation_error": job.auto_generation_error,
    }


@router.get("/jobs/{parsing_job_id}/generate-stream")
async def stream_generation(
    request: Request,
    parsing_job_id: int,
    db: DBSession,
    current_user: CurrentUser,
):
    job = await db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    return StreamingResponse(
        stream_gen_events(parsing_job_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{parsing_job_id}")
async def stream_progress(
    user: CurrentUser,
    parsing_job_id: int,
):
    # Auth is handled by the CurrentUser dependency, including query-token auth
    # Short-lived session for auth only — the stream itself must not hold a
    # DB connection open for its whole (possibly minutes-long) lifetime.
    async with async_session_maker() as session:
        job = await session.get(ParsingJob, parsing_job_id)
        if not job or job.user_id != user.id:
            raise HTTPException(status_code=404, detail="Parsing job not found")

    def _serialize(job: ParsingJob) -> str:
        return json.dumps(
            {
                "id": job.id,
                "query": job.query,
                "status": job.status,
                "saved_count": job.saved_count,
                "total_found": job.total_found,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "generation_mode": job.generation_mode.value,
                "error": job.error,
            }
        )

    async def event_generator() -> AsyncIterator[str]:
        # Poll the DB row, which the background worker keeps up to date. This
        # is stateless, so a reconnecting client (e.g. after a page reload)
        # always re-syncs to the true job state and still receives the final
        # status once the background parse finishes.
        last_payload: str | None = None
        while True:
            async with async_session_maker() as session:
                job = await session.get(ParsingJob, parsing_job_id)
                if job is None:
                    break
                payload = _serialize(job)
                terminal = job.status in ("done", "failed")
            if payload != last_payload:
                yield f"data: {payload}\n\n"
                last_payload = payload
            else:
                # Heartbeat (SSE comment) keeps idle connections alive through
                # proxies without triggering a client-side update.
                yield ": ping\n\n"
            if terminal:
                break
            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
