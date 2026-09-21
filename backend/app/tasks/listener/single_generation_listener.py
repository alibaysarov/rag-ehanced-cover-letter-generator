import json
import logging

from app.decorators.celery_response_listener import response_listener
from app.dependencies import get_websocket_manager

logger = logging.getLogger(__name__)

ws_manager = get_websocket_manager()


@response_listener("cover_letter_events")
async def handle_event(data: dict):
    # тут ваша реакция: обновить БД, отправить websocket-пуш клиенту,
    # проверить, все ли vacancy в batch_id завершились, и т.п.
    payload = dict(data)
    user_id = payload.pop("user_id", None)
    if user_id is None:
        logger.warning("Ignoring cover letter event without user_id: %r", data)
        return
    await ws_manager.send_text(str(user_id), json.dumps(payload))
    logger.info("cover letter event: %s", payload)


@response_listener("test_events")
async def handle_test_event(data: dict):
    payload = dict(data)
    user_id = payload.pop("user_id", None)
    if user_id is None:
        logger.warning("Ignoring test event without user_id: %r", data)
        return
    await ws_manager.send_text(str(user_id), json.dumps(payload))
    logger.info("cover letter event: %s", payload)
