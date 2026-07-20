import logging
from typing import List

from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import HTTPException

from app.dependencies import get_cv_service, get_user_service
from app.schemas.general import Option
from app.schemas.letter import GeneralResponse
from app.services import CVService, UserService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/cvs")
async def get_all_cvs(
    request: Request,
    user_service: UserService = Depends(get_user_service),
    cv_service: CVService = Depends(get_cv_service),
):
    user_email = request.state.user_email
    try:
        user = user_service.get_user_by_email(user_email)
        cvs = await cv_service.get_by_user(user.id)
        result = {"cvs": cvs}
        return GeneralResponse(success=True, data=result)
    except Exception as e:
        logging.error("Error retrieving CVs", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving CVs")


@router.get("/cvs/options")
async def get_cvs_by_user(
    request: Request,
    user_service: UserService = Depends(get_user_service),
    cv_service: CVService = Depends(get_cv_service),
):
    """Get cvs options by user"""
    user_email = request.state.user_email
    try:
        user = user_service.get_user_by_email(user_email)
    except Exception as e:
        logging.error("Error finding user", exc_info=True)
        raise HTTPException(status_code=404, detail="User Not found")
    options: List[Option] = await cv_service.get_cvs_by_user(user_id=user.id)
    result = {"options": options}
    return GeneralResponse(success=True, data=result)
