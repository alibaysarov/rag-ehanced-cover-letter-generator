import logging

from app.decorators.celery_response_listener import response_listener

logger = logging.getLogger(__name__)
import json

from app.dependencies import get_websocket_manager

ws_manager = get_websocket_manager()


@response_listener("cover_letter_events")
async def handle_event(data: dict):
    # тут ваша реакция: обновить БД, отправить websocket-пуш клиенту,
    # проверить, все ли vacancy в batch_id завершились, и т.п.
    user_id = data.get("user_id")
    data.pop("user_id")
    await ws_manager.send_text(user_id, json.dumps(data))
    logger.info("cover letter event: %s", data)
