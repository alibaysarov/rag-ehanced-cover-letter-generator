import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, HTTPException, UploadFile
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader

from app.api.v1.endpoints.user import get_cv_service
from app.services.cv import CVService
from app.schemas.letter import CVUploadResponse, GeneralResponse
from app.schemas.llm_outputs.cv_parse import CVImportModel
from app.services.llm.job_requirements import CVImportPrompt
from app.services.projects import ProjectStorageService, get_projects_service
from app.helper.user import get_user_repository
from app.repository.user_repository import UserRepository
from validator.pdf import validate_pdf_and_get_path

_pdf_reader = PDFReader()
_splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=0)


def get_projects_storage_service() -> ProjectStorageService:
    return get_projects_service()

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/import")
async def cv_import(
    request: Request,
    file: UploadFile = File(..., description="PDF file containing the CV/resume"),
    source_id: str = Form(None, description="Optional source identifier; generated if not provided"),
    user_repo: UserRepository = Depends(get_user_repository),
    projects_service: ProjectStorageService = Depends(get_projects_storage_service),
):
    user_email = request.state.user_email
    user = user_repo.get_user_by_email(user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_data = await validate_pdf_and_get_path(file)
    try:
        docs = _pdf_reader.load_data(file=file_data["temp_file_path"])
        texts = [d.text for d in docs if getattr(d, "text", None)]
        chunks = []
        for t in texts:
            chunks.extend(_splitter.split_text(t))
        cv_text = " ".join(chunks)

        cv_import_prompt = CVImportPrompt()
        chain = cv_import_prompt.prompt_template | cv_import_prompt.get_model
        result: CVImportModel = chain.invoke({"cv_text": cv_text})

        effective_source_id = source_id or str(uuid.uuid4())
        saved = projects_service.save_projects(
            user_id=user.id,
            source_id=effective_source_id,
            projects=result.projects,
        )

        return {
            "raw_text": cv_text,
            "result": result,
            "source_id": effective_source_id,
            "saved_projects": saved,
        }
    finally:
        if os.path.exists(file_data["temp_file_path"]):
            os.unlink(file_data["temp_file_path"])


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