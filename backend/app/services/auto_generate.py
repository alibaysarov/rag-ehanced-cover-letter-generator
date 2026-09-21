import json
from typing import AsyncIterator

from fastapi import Request

from app.cache import sync_client
from app.cache.redis import async_client
from app.models import AutoParsedJob
from app.repository.parsing_job_repository import ParsingJobRepository
from app.schemas.generation_mode import GenerationMode


def start_test_batch(user_id: int, parsing_job_id: int, vacancy_ids: list[int]):
    # Import lazily: parse_site invokes the auto-start service after parsing,
    # while the tasks package imports parse_site during application startup.
    from app.tasks.single_generation import test_task

    first_name = "ali"
    last_name = "baisarov"

    for vacancy_id in vacancy_ids:
        test_task.delay(user_id, vacancy_id, first_name, last_name, parsing_job_id)


def start_batch(
    user_id: int,
    parsing_job_id: int,
    vacancy_ids: list[int],
    first_name,
    last_name,
    generation_mode: str = "ai",
):
    # See start_test_batch: a module-level import would create a cycle with
    # app.tasks.parse_site -> this module.
    from app.tasks.single_generation import single_generation

    # инициализируем счётчик total, чтобы понимать, когда всё закончилось
    sync_client.hset(f"batch_meta:{parsing_job_id}", "total", len(vacancy_ids))

    for vacancy_id in vacancy_ids:
        single_generation.delay(
            user_id,
            vacancy_id,
            first_name,
            last_name,
            parsing_job_id,
            generation_mode=generation_mode,
        )

    return parsing_job_id


def start_single_template_generation(
    user_id: int,
    parsing_job_id: int,
    vacancy_id: int,
) -> None:
    """Add one vacancy to a growing template batch and dispatch its task."""
    from app.tasks.single_generation import single_generation

    meta_key = f"batch_meta:{parsing_job_id}"
    sync_client.hincrby(meta_key, "total", 1)
    sync_client.expire(meta_key, 3600)
    try:
        single_generation.delay(
            user_id,
            vacancy_id,
            "",
            "",
            parsing_job_id,
            generation_mode=GenerationMode.TEMPLATE.value,
        )
    except Exception:
        sync_client.hincrby(meta_key, "total", -1)
        raise


async def maybe_start_template_generation_for_vacancy(
    vacancy: AutoParsedJob,
    generation_mode: GenerationMode,
    repository: ParsingJobRepository,
) -> bool:
    """Dispatch generation immediately after one vacancy is persisted."""
    if generation_mode != GenerationMode.TEMPLATE:
        return False
    if vacancy.id is None or vacancy.parsing_job_id is None:
        raise ValueError("Saved parsing vacancy is missing public identifiers")
    try:
        start_single_template_generation(
            vacancy.user_id,
            vacancy.parsing_job_id,
            vacancy.id,
        )
        await repository.record_template_generation_started(vacancy.parsing_job_id)
        return True
    except Exception as exc:
        await repository.set_auto_generation_error(
            vacancy.parsing_job_id, str(exc)[:500]
        )
        raise


async def stream_gen_events(
    parsing_job_id: int, request: Request
) -> AsyncIterator[str]:
    """
    Сначала отдаёт снапшот уже накопленных статусов из batch:{parsing_job_id},
    затем подписывается на batch_channel:{parsing_job_id} и стримит live-события,
    пока не завершатся все таски батча (или клиент не отключится).
    """
    pubsub = async_client.pubsub()

    try:
        await pubsub.subscribe(f"batch_channel:{parsing_job_id}")

        # --- 1. снапшот текущего состояния ---
        snapshot = await async_client.hgetall(f"batch:{parsing_job_id}")
        seen_vacancy_ids = set(snapshot.keys())

        yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"

        terminal_statuses = {"generated", "failed", "not_found"}
        finished_count = sum(
            1 for v in snapshot.values() if json.loads(v)["status"] in terminal_statuses
        )

        total_raw = await async_client.hget(f"batch_meta:{parsing_job_id}", "total")
        total = int(total_raw) if total_raw else None

        # если метаданных о батче нет вообще и снапшот пуст — генерация не запускалась
        if total is None and not snapshot:
            return

        # если total неизвестен (batch_meta уже подчищен) — считаем, что всё завершено
        if total is None:
            yield "event: complete\ndata: {}\n\n"
            return

        # --- 2. живой стрим ---
        while finished_count < total:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(
                timeout=15, ignore_subscribe_messages=True
            )

            if message is None:
                yield ": heartbeat\n\n"
                continue

            data = message["data"]
            payload = json.loads(data)
            vacancy_id = str(payload["vacancy_id"])

            # защита от дублей, если то же событие уже было в снапшоте
            if (
                vacancy_id in seen_vacancy_ids
                and payload["status"] not in terminal_statuses
            ):
                pass

            yield f"data: {data}\n\n"

            if payload["status"] in terminal_statuses:
                finished_count += 1
                seen_vacancy_ids.add(vacancy_id)

        yield "event: complete\ndata: {}\n\n"

    finally:
        await pubsub.unsubscribe(f"batch_channel:{parsing_job_id}")
        await pubsub.close()
        await async_client.close()
