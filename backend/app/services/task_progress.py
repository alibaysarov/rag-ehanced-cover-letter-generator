import json

from app.cache.redis import sync_client

STREAM_KEY = "created_cover_letters"


def set_cover_letter_task_status(batch_id, vacancy_id, status, extra=None):
    payload = {"vacancy_id": vacancy_id, "status": status, **(extra or {})}
    data = json.dumps(payload)

    sync_client.hset(f"batch:{batch_id}", str(vacancy_id), data)
    sync_client.expire(f"batch:{batch_id}", 3600)
    sync_client.publish(f"batch_channel:{batch_id}", data)

    sync_client.xadd(
        STREAM_KEY,
        {
            "batch_id": str(batch_id),
            "vacancy_id": str(vacancy_id),
            "status": status,
        },
        maxlen=100_000,  # не даём стриму расти бесконечно, старое подрезается
        approximate=True,
    )

    if status in ("generated", "failed", "not_found"):
        terminal_count = sum(
            1
            for v in sync_client.hvals(f"batch:{batch_id}")
            if json.loads(v)["status"] in ("generated", "failed", "not_found")
        )
        total = int(sync_client.hget(f"batch_meta:{batch_id}", "total") or 0)
        if terminal_count >= total:
            sync_client.delete(f"batch_meta:{batch_id}")
        sync_client.hset(f"batch_meta:{batch_id}", "total", total)
