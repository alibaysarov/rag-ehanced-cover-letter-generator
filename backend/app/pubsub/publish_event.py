import json
import logging

from app.cache.redis import async_client as redis
from app.cache.redis import sync_client

logger = logging.getLogger(__name__)


def publish_event_sync(channel_name: str, data: dict):
    try:
        sync_client.publish(channel_name, json.dumps(data))
    except Exception as e:
        logger.error("Error during publishing event: %s", e)


async def publish_event(channel_name: str, data: dict):
    try:
        await redis.publish(
            channel_name,
            json.dumps(data),
        )
    except Exception as e:
        logger.error("Error during publishing event", e)
