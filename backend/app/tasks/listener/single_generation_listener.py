import logging

from app.decorators.celery_response_listener import response_listener

logger = logging.getLogger(__name__)


@response_listener("cover_letter_events")
async def handle_event(data: dict):
    # тут ваша реакция: обновить БД, отправить websocket-пуш клиенту,
    # проверить, все ли vacancy в batch_id завершились, и т.п.
    logger.info("cover letter event: %s", data)
