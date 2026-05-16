import os

import redis.asyncio as redis
redis_client = None

async def connect_redis():
    global redis_client

    redis_client = redis.Redis(
        host="redis",
        port=6379,
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )

    await redis_client.ping()


async def close_conn():
    global redis_client

    if redis_client:
        await redis_client.close()