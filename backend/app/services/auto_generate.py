import json
from typing import AsyncIterator

from fastapi import Request

from app.cache import sync_client
from app.cache.redis import async_client
from app.repository.auto_parse_job_repository import AutoParseJobRepository
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


async def maybe_start_template_generation(
    job_id: int, repository: ParsingJobRepository, session_factory
) -> bool:
    """Dispatch a template batch exactly once after the parent parsing transaction."""
    claimed = await repository.claim_template_generation(job_id)
    if claimed is None:
        return False
    if claimed.saved_count == 0:
        return True
    try:
        async with session_factory() as session:
            vacancies = await AutoParseJobRepository(session).get_by_job_id(job_id)
        start_batch(
            claimed.user_id,
            job_id,
            [v.id for v in vacancies if v.id is not None],
            "",
            "",
            GenerationMode.TEMPLATE.value,
        )
        return True
    except Exception as exc:
        await repository.set_auto_generation_error(job_id, str(exc)[:500])
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
