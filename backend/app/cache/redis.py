import os

import redis as sync_redis
import redis.asyncio as redis

REDIS_URL = "redis://:pass@redis:6379/0"

sync_client = sync_redis.Redis.from_url(REDIS_URL, decode_responses=True)

async_client = redis.from_url(REDIS_URL, decode_responses=True)

redis_client: redis.Redis | None = None


async def connect_redis():
    global redis_client

    redis_client = redis.Redis(
        host="redis",
        port=6379,
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )

    await redis_client.ping()


async def close_conn():
    global redis_client

    if redis_client:
        await redis_client.close()
