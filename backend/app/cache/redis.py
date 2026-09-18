import os
from urllib.parse import quote

import redis as sync_redis
import redis.asyncio as redis

_redis_password = os.getenv("REDIS_PASSWORD")
REDIS_URL = os.getenv("REDIS_URL") or (
    f"redis://:{quote(_redis_password, safe='')}@"
    f"{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0"
    if _redis_password
    else f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0"
)

sync_client = sync_redis.Redis.from_url(REDIS_URL, decode_responses=True)

async_client = redis.from_url(REDIS_URL, decode_responses=True)

redis_client: redis.Redis | None = None


async def connect_redis():
    global redis_client

    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
    )

    await redis_client.ping()


async def close_conn():
    global redis_client

    if redis_client:
        await redis_client.close()
