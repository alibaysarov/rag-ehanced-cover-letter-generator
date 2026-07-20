import csv
import io
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.dependencies import get_sent_letter_repository
from app.helper.user import CurrentUser
from app.repository.sent_cover_letter_repository import SentCoverLetterRepository

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
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sent-letters", response_model=SentCoverLetterRead, status_code=201)
async def create_sent_letter(
    user: CurrentUser,
    body: SentCoverLetterCreate,
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):
    record = await repo.create(
        user_id=user.id,
        url=body.url,
        job_name=body.job_name,
        letter_text=body.letter_text,
        generation_time_ms=body.generation_time_ms,
    )
    return SentCoverLetterRead.model_validate(record)


@router.get("/sent-letters", response_model=SentCoverLetterListResponse)
async def list_sent_letters(
    user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    type: Optional[str] = Query(default=None),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):

    items, total = await repo.get_list(
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
async def update_sent_letter(
    user: CurrentUser,
    record_id: int,
    body: SentCoverLetterUpdate,
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):

    record = await repo.update_accepted(
        record_id=record_id, user_id=user.id, is_accepted=body.is_accepted
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return SentCoverLetterRead.model_validate(record)


@router.get("/sent-letters/export-csv")
async def export_sent_letters_csv(
    user: CurrentUser,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):
    rows = await repo.get_summary(user_id=user.id, date_from=date_from, date_to=date_to)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Дата", "LinkedIn", "hh.ru", "Другие", "Итого", "Потрачено времени"]
    )
    for row in rows:
        writer.writerow(
            [
                row["date"],
                row["linkedin"],
                row["hh_ru"],
                row["other"],
                row["total"],
                row.get("time_spent", "—"),
            ]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="applications.csv"'},
    )


@router.get("/sent-letters/summary", response_model=list[SummaryRow])
async def sent_letters_summary(
    user: CurrentUser,
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    repo: SentCoverLetterRepository = Depends(get_sent_letter_repository),
):
    rows = await repo.get_summary(user_id=user.id, date_from=date_from, date_to=date_to)
    return [SummaryRow(**row) for row in rows]
