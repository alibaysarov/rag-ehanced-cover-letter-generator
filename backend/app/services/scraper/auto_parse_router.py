import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select, desc

from app.database import get_db
from app.helper.user import get_user_repository
from app.models.auto_parsed_job import AutoParsedJob
from app.models.parsing_job import ParsingJob
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository
from app.repository.user_repository import UserRepository
from app.services.jwt import JwtService
from app.services.scraper.hh_scraper import get_or_create_queue, remove_queue, run_parse_job

logger = logging.getLogger(__name__)
router = APIRouter()
jwt_service = JwtService()


def _get_user_from_request(request: Request, user_repo: UserRepository) -> int:
    email = request.state.user_email
    user = user_repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.id


class StartParseRequest(BaseModel):
    query: str


class MarkAppliedRequest(BaseModel):
    letter_text: str = ""


@router.post("/start")
async def start_parse(
    body: StartParseRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user_id = _get_user_from_request(request, user_repo)

    parsing_job = ParsingJob(user_id=user_id, query=body.query, status="pending")
    db.add(parsing_job)
    db.commit()
    db.refresh(parsing_job)

    asyncio.create_task(run_parse_job(parsing_job.id, body.query, user_id))

    return {"parsing_job_id": parsing_job.id}


@router.get("/status/{parsing_job_id}")
def get_status(
    parsing_job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user_id = _get_user_from_request(request, user_repo)
    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Parsing job not found")
    return job


@router.get("/jobs/{parsing_job_id}/vacancies")
def get_vacancies(
    parsing_job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user_id = _get_user_from_request(request, user_repo)
    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    vacancies = db.exec(
        select(AutoParsedJob)
        .where(AutoParsedJob.parsing_job_id == parsing_job_id)
        .order_by(AutoParsedJob.id)
    ).all()
    return vacancies


@router.patch("/vacancies/{vacancy_id}/applied")
def mark_applied(
    vacancy_id: int,
    body: MarkAppliedRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user_id = _get_user_from_request(request, user_repo)
    vacancy = db.get(AutoParsedJob, vacancy_id)
    if not vacancy or vacancy.user_id != user_id:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    vacancy.is_applied = True
    db.add(vacancy)

    sent_repo = SentCoverLetterRepository(db)
    sent_repo.create(
        user_id=user_id,
        url=vacancy.url,
        job_name=vacancy.job_title,
        letter_text=body.letter_text or vacancy.job_title,
    )

    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.get("/history")
def get_history(
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    user_id = _get_user_from_request(request, user_repo)
    jobs = db.exec(
        select(ParsingJob)
        .where(ParsingJob.user_id == user_id)
        .order_by(desc(ParsingJob.id))
    ).all()
    return jobs


@router.post("/jobs/{parsing_job_id}/generate")
async def start_generate(
    parsing_job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    from app.services.scraper.batch_cover_letter import (
        mark_generating, get_or_create_gen_progress, run_batch_generation
    )

    user_id = _get_user_from_request(request, user_repo)
    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Parsing job not found")
    if job.status != "done":
        raise HTTPException(status_code=400, detail="Parsing job is not done yet")

    if not mark_generating(parsing_job_id):
        raise HTTPException(status_code=409, detail="Generation already in progress")

    get_or_create_gen_progress(parsing_job_id)
    asyncio.create_task(run_batch_generation(parsing_job_id, user_id))

    return {"status": "started"}


@router.get("/jobs/{parsing_job_id}/generate-status")
def get_generate_status(
    parsing_job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user_repo: UserRepository = Depends(get_user_repository),
):
    from app.services.scraper.batch_cover_letter import _running_generations

    user_id = _get_user_from_request(request, user_repo)
    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user_id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    vacancies = db.exec(
        select(AutoParsedJob)
        .where(AutoParsedJob.parsing_job_id == parsing_job_id)
    ).all()

    total = len(vacancies)
    generated = sum(1 for v in vacancies if v.is_generated)

    return {
        "is_running": parsing_job_id in _running_generations,
        "generated": generated,
        "total": total,
    }


@router.get("/jobs/{parsing_job_id}/generate-stream")
async def stream_generation(
    parsing_job_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    from app.services.scraper.batch_cover_letter import (
        stream_gen_events, _running_generations, remove_gen_progress
    )

    try:
        payload = jwt_service.decode_jwt(token)
        email = payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.repository.user_repository import UserRepository as UR
    user_repo = UR(db)
    user = user_repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event_data in stream_gen_events(parsing_job_id):
                yield f"data: {event_data}\n\n"
        finally:
            # Clean up only after generation is fully done
            if parsing_job_id not in _running_generations:
                remove_gen_progress(parsing_job_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream/{parsing_job_id}")
async def stream_progress(
    parsing_job_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    # Auth via query param (EventSource can't set headers)
    try:
        payload = jwt_service.decode_jwt(token)
        email = payload.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    from app.repository.user_repository import UserRepository as UR
    user_repo = UR(db)
    user = user_repo.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job = db.get(ParsingJob, parsing_job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Parsing job not found")

    queue = get_or_create_queue(parsing_job_id)

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=60)
                if item is None:
                    break
                yield f"data: {item}\n\n"
                data = json.loads(item)
                if data.get("status") in ("done", "failed"):
                    break
        except asyncio.TimeoutError:
            pass
        finally:
            remove_queue(parsing_job_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
