import asyncio
from functools import wraps

from app.database import celery_engine


def async_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        async def runner():
            try:
                return await func(*args, **kwargs)
            finally:
                await celery_engine.dispose()

        return asyncio.run(runner())

    return wrapper
