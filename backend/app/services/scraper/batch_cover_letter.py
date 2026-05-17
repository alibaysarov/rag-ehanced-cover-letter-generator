import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

from sqlmodel import Session, select

from app.database import engine
from app.models.auto_parsed_job import AutoParsedJob
from app.repository.user_repository import UserRepository
from app.services.cover_letter import CoverLetterService

logger = logging.getLogger(__name__)

_running_generations: set[int] = set()
_GPU_SEMAPHORE: asyncio.Semaphore | None = None


@dataclass
class GenProgress:
    events: list[str] = field(default_factory=list)
    finished: bool = False


_gen_progress: dict[int, GenProgress] = {}


def _get_gpu_semaphore() -> asyncio.Semaphore:
    global _GPU_SEMAPHORE
    if _GPU_SEMAPHORE is None:
        _GPU_SEMAPHORE = asyncio.Semaphore(2)  # RTX 4060 8GB, max 2 concurrent mistral:7b
    return _GPU_SEMAPHORE


def get_or_create_gen_progress(parsing_job_id: int) -> GenProgress:
    if parsing_job_id not in _gen_progress:
        _gen_progress[parsing_job_id] = GenProgress()
    return _gen_progress[parsing_job_id]


def remove_gen_progress(parsing_job_id: int) -> None:
    _gen_progress.pop(parsing_job_id, None)


def mark_generating(parsing_job_id: int) -> bool:
    """Returns True if successfully marked (not already running), False if already running."""
    if parsing_job_id in _running_generations:
        return False
    _running_generations.add(parsing_job_id)
    return True


async def stream_gen_events(parsing_job_id: int) -> AsyncIterator[str]:
    """Yields SSE event payloads. Replays all past events first, then follows live ones."""
    progress = _gen_progress.get(parsing_job_id)
    if progress is None:
        return

    pos = 0
    while True:
        while pos < len(progress.events):
            yield progress.events[pos]
            pos += 1
        if progress.finished:
            break
        await asyncio.sleep(0.3)


async def _generate_one(
    vacancy_id: int,
    job_title: str,
    job_text: str,
    user_id: int,
    progress: GenProgress,
    counter: dict,
    total: int,
) -> None:
    semaphore = _get_gpu_semaphore()
    async with semaphore:
        try:
            with Session(engine) as db:
                user_repo = UserRepository(db)
                service = CoverLetterService(user_repo)

                full_text = ""
                async for delta in service.stream_by_text(job_title, job_text, user_id):
                    full_text += delta

            with Session(engine) as db:
                v = db.get(AutoParsedJob, vacancy_id)
                if v:
                    v.cover_letter_text = full_text
                    v.is_generated = True
                    db.add(v)
                    db.commit()

        except Exception as e:
            logger.error(f"Failed to generate cover letter for vacancy {vacancy_id}: {e}")

        finally:
            counter["generated"] += 1
            progress.events.append(json.dumps({
                "generated": counter["generated"],
                "total": total,
                "status": "running",
                "vacancy_id": vacancy_id,
            }))


async def run_batch_generation(parsing_job_id: int, user_id: int) -> None:
    progress = get_or_create_gen_progress(parsing_job_id)
    try:
        with Session(engine) as db:
            vacancies = db.exec(
                select(AutoParsedJob)
                .where(AutoParsedJob.parsing_job_id == parsing_job_id)
                .where(AutoParsedJob.is_generated == False)  # noqa: E712
            ).all()

        total = len(vacancies)
        if total == 0:
            progress.events.append(json.dumps({"generated": 0, "total": 0, "status": "done"}))
            return

        counter = {"generated": 0}
        tasks = [
            asyncio.create_task(
                _generate_one(v.id, v.job_title, v.job_text, user_id, progress, counter, total)
            )
            for v in vacancies
        ]
        await asyncio.gather(*tasks)

        progress.events.append(json.dumps({"generated": total, "total": total, "status": "done"}))

    except Exception as e:
        logger.error(f"Batch generation failed for parsing_job {parsing_job_id}: {e}")
        progress.events.append(json.dumps({"generated": 0, "total": 0, "status": "failed"}))

    finally:
        _running_generations.discard(parsing_job_id)
        progress.finished = True
