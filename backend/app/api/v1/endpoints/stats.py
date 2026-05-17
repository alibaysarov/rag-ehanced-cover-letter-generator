import csv
import io
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_db
from app.helper.user import get_user_repository
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository
from app.repository.user_repository import UserRepository

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class SentCoverLetterCreate(BaseModel):
    url: Optional[str] = None
    job_name: Optional[str] = None
    letter_text: str
    generation_time_ms: Optional[int] = None


class SentCoverLetterRead(BaseModel):
    id: int
    url: Optional[str]
    job_name: Optional[str]
    type: str
    is_accepted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SentCoverLetterUpdate(BaseModel):
    is_accepted: bool


class SentCoverLetterListResponse(BaseModel):
    items: list[SentCoverLetterRead]
    total: int
    page: int
    page_size: int


class SummaryRow(BaseModel):
    date: str
    hh_ru: int
    linkedin: int
    other: int
    total: int
    time_spent: str = "—"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_sent_letter_repo(db: Session = Depends(get_db)) -> SentCoverLetterRepository:
    return SentCoverLetterRepository(db)


def _get_current_user(request: Request, user_repo: UserRepository):
    user_email = request.state.user_email
    user = user_repo.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sent-letters", response_model=SentCoverLetterRead, status_code=201)
def create_sent_letter(
    body: SentCoverLetterCreate,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repo),
):
    user = _get_current_user(request, user_repo)
    record = repo.create(
        user_id=user.id,
        url=body.url,
        job_name=body.job_name,
        letter_text=body.letter_text,
        generation_time_ms=body.generation_time_ms,
    )
    return SentCoverLetterRead.model_validate(record)


@router.get("/sent-letters", response_model=SentCoverLetterListResponse)
def list_sent_letters(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    type: Optional[str] = Query(default=None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repo),
):
    user = _get_current_user(request, user_repo)
    items, total = repo.get_list(
        user_id=user.id,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        type_filter=type,
    )
    return SentCoverLetterListResponse(
        items=[SentCoverLetterRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.put("/sent-letters/{record_id}", response_model=SentCoverLetterRead)
def update_sent_letter(
    record_id: int,
    body: SentCoverLetterUpdate,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repo),
):
    user = _get_current_user(request, user_repo)
    record = repo.update_accepted(record_id=record_id, user_id=user.id, is_accepted=body.is_accepted)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return SentCoverLetterRead.model_validate(record)


@router.get("/sent-letters/export-csv")
def export_sent_letters_csv(
    request: Request,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repo),
):
    user = _get_current_user(request, user_repo)
    rows = repo.get_summary(user_id=user.id, date_from=date_from, date_to=date_to)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Дата", "LinkedIn", "hh.ru", "Другие", "Итого", "Потрачено времени"])
    for row in rows:
        writer.writerow([row["date"], row["linkedin"], row["hh_ru"], row["other"], row["total"], row.get("time_spent", "—")])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="applications.csv"'},
    )


@router.get("/sent-letters/summary", response_model=list[SummaryRow])
def sent_letters_summary(
    request: Request,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    user_repo: UserRepository = Depends(get_user_repository),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repo),
):
    user = _get_current_user(request, user_repo)
    rows = repo.get_summary(user_id=user.id, date_from=date_from, date_to=date_to)
    return [SummaryRow(**row) for row in rows]
