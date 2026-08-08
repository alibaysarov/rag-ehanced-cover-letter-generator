import asyncio
import json
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from app.cache.redis import async_client as redis

logger = logging.getLogger(__name__)

Listener = Callable[[dict], Awaitable[None]]


class PubsubListener:
    def __init__(self):
        self._listeners: dict[str, list[Listener]] = defaultdict(list)
        self._tasks: list[asyncio.Task] = []

    def attach_listener(self, channel: str, func):
        self._listeners[channel].append(func)

    def start_all_listeners(self) -> list[asyncio.Task]:
        result = [
            asyncio.create_task(self.__run_channel_listener(chan, handlers))
            for chan, handlers in self._listeners.items()
        ]
        self._tasks = result

    async def stop_all_listeners(self):
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def __run_channel_listener(self, redis_chan: str, handlers: list[Listener]):
        pubsub = redis.pubsub()
        await pubsub.subscribe(redis_chan)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                except Exception:
                    logger.exception("failed to handle event")
                for handler in handlers:
                    try:
                        await handler(data)
                    except Exception:
                        logger.exception(
                            "handler %s failed on %s", handler.__name__, redis_chan
                        )
        finally:
            await pubsub.unsubscribe(redis_chan)
            await redis.aclose()
