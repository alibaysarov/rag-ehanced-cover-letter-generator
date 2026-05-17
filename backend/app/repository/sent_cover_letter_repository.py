import logging
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session, select, func, col

from app.models.sent_cover_letter import SentCoverLetter

logger = logging.getLogger(__name__)


def _detect_type(url: Optional[str]) -> str:
    if not url:
        return "other"
    if "hh.ru" in url:
        return "hh_ru"
    if "linkedin.com" in url:
        return "linkedin"
    return "other"


class SentCoverLetterRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, url: Optional[str], job_name: Optional[str], letter_text: str, generation_time_ms: Optional[int] = None) -> SentCoverLetter:
        record = SentCoverLetter(
            user_id=user_id,
            url=url,
            job_name=job_name,
            letter_text=letter_text,
            type=_detect_type(url),
            generation_time_ms=generation_time_ms,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        type_filter: Optional[str] = None,
    ) -> tuple[list[SentCoverLetter], int]:
        stmt = select(SentCoverLetter).where(SentCoverLetter.user_id == user_id)
        stmt = self._apply_filters(stmt, date_from, date_to, type_filter)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = self.session.exec(count_stmt).one()

        stmt = stmt.order_by(col(SentCoverLetter.created_at).desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(self.session.exec(stmt).all())
        return items, total

    def update_accepted(self, record_id: int, user_id: int, is_accepted: bool) -> Optional[SentCoverLetter]:
        stmt = select(SentCoverLetter).where(
            SentCoverLetter.id == record_id,
            SentCoverLetter.user_id == user_id,
        )
        record = self.session.exec(stmt).first()
        if not record:
            return None
        record.is_accepted = is_accepted
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_for_export(
        self,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        type_filter: Optional[str] = None,
    ) -> list[SentCoverLetter]:
        stmt = select(SentCoverLetter).where(SentCoverLetter.user_id == user_id)
        stmt = self._apply_filters(stmt, date_from, date_to, type_filter)
        stmt = stmt.order_by(col(SentCoverLetter.created_at).asc())
        return list(self.session.exec(stmt).all())

    def get_summary(
        self,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[dict]:
        """Return per-day counts grouped by type, sorted by date ascending."""
        records = self.get_for_export(user_id, date_from, date_to, type_filter=None)

        # Python-side aggregation: group by date + type
        aggregated: dict[str, dict] = {}
        for r in records:
            day = r.created_at.date().isoformat()
            if day not in aggregated:
                aggregated[day] = {"date": day, "hh_ru": 0, "linkedin": 0, "other": 0, "total": 0}
            if r.type == "hh_ru":
                aggregated[day]["hh_ru"] += 1
            elif r.type == "linkedin":
                aggregated[day]["linkedin"] += 1
            else:
                aggregated[day]["other"] += 1
            aggregated[day]["total"] += 1

        return sorted(aggregated.values(), key=lambda x: x["date"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_filters(self, stmt, date_from: Optional[date], date_to: Optional[date], type_filter: Optional[str]):
        if date_from:
            stmt = stmt.where(SentCoverLetter.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            stmt = stmt.where(SentCoverLetter.created_at <= datetime.combine(date_to, datetime.max.time()))
        if type_filter:
            stmt = stmt.where(SentCoverLetter.type == type_filter)
        return stmt
