import logging

from fastapi import APIRouter, Depends, File, Form, Request,HTTPException, UploadFile

from app.api.v1.endpoints.user import get_cv_service
from app.services.cv import CVService
from app.schemas.letter import CVUploadResponse, GeneralResponse
from app.helper.user import get_user_repository
from app.repository.user_repository import UserRepository
from validator.pdf import validate_pdf_and_get_path

logger = logging.getLogger(__name__)
router = APIRouter()

@router.put("/{cv_id}")
async def update_cv(
    cv_id: int,
    source_id: str = Form(..., description="Unique identifier for the CV source"),
    file: UploadFile = File(..., description="PDF file containing the CV/resume"),
    cv_service:CVService = Depends(get_cv_service)
):
    file_data = await validate_pdf_and_get_path(file)
    
    try:
        await cv_service.update_cv(
            cv_id=cv_id,
            source_id=source_id,
            pdf_path=file_data["temp_file_path"],
            filename=file.filename,
            original_filename=file.filename,
            file_size=len(file_data["file_content"]),
            content_type=file.content_type or "application/pdf"
        )

        return CVUploadResponse(
            success=True,
            message=f"CV updated successfully with id: {cv_id}",
            source_id=cv_id,
            data={
                "filename": file.filename,
                "file_size": len(file_data["file_content"]),
                "source_id": cv_id
            }
        )
    finally:
        # Clean up temporary file
        import os
        if os.path.exists(file_data["temp_file_path"]):
            os.unlink(file_data["temp_file_path"])


@router.delete("/{cv_id}")
async def delete_cv(
    cv_id: int,
    request: Request,
    cv_service:CVService = Depends(get_cv_service)
    ):
    """Delete CV by id with rollback support."""
    try:
        await cv_service.delete_cv(cv_id)
        return GeneralResponse(
            success=True,
            message=f"CV with id {cv_id} deleted successfully"
        )
    except Exception as e:
        logging.error("Error retrieving CVs", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving CVs")  


def _get_user_by_mail(email:str,user_repo: UserRepository):
    current_user = user_repo.get_user_by_email(email)
    return current_user