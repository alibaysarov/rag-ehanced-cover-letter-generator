import json

import redis as sync_redis

REDIS_URL = "redis://:pass@redis:6379/0"

_sync_client = sync_redis.Redis.from_url(REDIS_URL)


def set_cover_letter_task_status(batch_id, vacancy_id, status, extra=None):
    payload = {"vacancy_id": vacancy_id, "status": status, **(extra or {})}
    data = json.dumps(payload)

    _sync_client.hset(f"batch:{batch_id}", str(vacancy_id), data)
    _sync_client.expire(f"batch:{batch_id}", 3600)
    _sync_client.publish(f"batch_channel:{batch_id}", data)

    if status in ("generated", "failed", "not_found"):
        terminal_count = sum(
            1
            for v in _sync_client.hvals(f"batch:{batch_id}")
            if json.loads(v)["status"] in ("generated", "failed", "not_found")
        )
        total = int(_sync_client.hget(f"batch_meta:{batch_id}", "total") or 0)
        if terminal_count >= total:
            _sync_client.delete(f"batch_meta:{batch_id}")
