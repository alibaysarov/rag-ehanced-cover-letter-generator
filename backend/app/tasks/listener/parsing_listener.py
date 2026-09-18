import json
import logging

from pydantic import ValidationError

from app.decorators.celery_response_listener import response_listener
from app.dependencies import get_websocket_manager
from app.schemas.api.auto_parse import ParsingVacancySavedEvent

logger = logging.getLogger(__name__)
ws_manager = get_websocket_manager()


@response_listener("parsing_events")
async def handle_parsing_event(data: dict) -> None:
    try:
        event = ParsingVacancySavedEvent.model_validate(data)
        if (
            event.type != "parsing.vacancy_saved"
            or event.vacancy.parsing_job_id != event.parsing_job_id
        ):
            raise ValueError("inconsistent parsing event")
    except (ValidationError, ValueError):
        logger.warning("Ignoring invalid parsing event: %r", data)
        return
    payload = event.model_dump(mode="json", exclude={"user_id"})
    await ws_manager.send_text(str(event.user_id), json.dumps(payload))
