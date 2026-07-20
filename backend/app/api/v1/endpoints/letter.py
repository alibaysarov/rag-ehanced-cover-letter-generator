import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import DBSession, get_cover_letter_service, get_letter_service
from app.helper.user import CurrentUser
from app.schemas.letter import CVUploadResponse, LetterResponse

logger = logging.getLogger(__name__)

router = APIRouter()


async def _sse_wrap(
    generator: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    try:
        async for delta in generator:
            if delta == "__URL_PARSE_ERROR__":
                yield f"data: {json.dumps({'error': 'URL_PARSE_ERROR'})}\n\n"
                return
            elif delta in ("__PARSING__", "__READY__"):
                yield f"data: {json.dumps({'status': delta})}\n\n"
            else:
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        yield "data: [DONE]\n\n"
    except ValueError as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    except Exception as exc:
        logger.exception("Streaming error")
        yield f"data: {json.dumps({'error': 'Internal streaming error'})}\n\n"




async def fetch(name, delay):
    print(f"{name}: начало")
    await asyncio.sleep(delay)  # имитация сетевого запроса
    print(f"{name}: готово")
    return name

@router.post("/async-test",response_model=CVUploadResponse)
async def load_test(
    user:CurrentUser,
    file: UploadFile = File(..., description="PDF file containing the CV/resume"),
    source_id: str = Form(..., description="Unique identifier for the CV source"),
    
    letter_service: LetterService = Depends(get_letter_service),
):
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")

        # Save file temporarily
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            
            
            await letter_service.parse_cv(
                user_id=user.id,
                pdf_path=temp_file_path,
                source_id=source_id,
                filename=file.filename,
                original_filename=file.filename,
                file_size=len(file_content),
                content_type=file.content_type or "application/pdf"
            )

            return CVUploadResponse(
                success=True,
                message=f"CV uploaded successfully with source_id: {source_id}",
                source_id=source_id,
                data={
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "source_id": source_id
                }
            )

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error uploading CV", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading CV: {str(e)}")
    

@router.post("/url", response_model=LetterResponse)
async def create_letter_from_url(
    url: str = Form(..., description="URL to extract content from"),
    source_id: int = Form(..., description="Source ID of the CV in the database"),
    letter_service: LetterService = Depends(get_letter_service),
):
    """
    Create a cover letter from a URL source.

    - **url**: URL to extract content from
    - **source_id**: Source ID of the CV in the database
    """
    try:
        # Validate URL
        http_url = HttpUrl(url)

        # Generate cover letter from URL
        letter_content = await letter_service.generate_by_url(str(http_url), source_id)

        if letter_content.startswith("Ошибка") or letter_content.startswith("Не удалось"):
            raise HTTPException(status_code=500, detail=letter_content)

        result = {
            "url": str(http_url),
            "source_id": source_id,
            "letter_content": letter_content
        }

        return LetterResponse(
            success=True,
            message="Cover letter generated successfully from URL",
            data=result
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/url/stream")
async def stream_letter_from_url(
    user:CurrentUser,
    url: str = Form(...),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):
    http_url = HttpUrl(url)


    return StreamingResponse(
        _sse_wrap(cover_letter_service.stream_by_url(str(http_url), user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/url/test")
async def create_letter_from_url_test(
    user:CurrentUser,
    url: str = Form(..., description="URL to extract content from"),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):
    try:
        http_url = HttpUrl(url)

        result = await cover_letter_service.sync_by_url(str(http_url), user.id)
        return {"result": result}

    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error generating cover letter (test)", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))



@router.post("/text", response_model=LetterResponse)
async def create_letter_from_text(
    name: str = Form(..., min_length=1, max_length=100, description="Job title"),
    description: str = Form(..., min_length=1, description="Job description"),
    source_id: int = Form(..., description="Source ID of the CV in the database"),
    letter_service: LetterService = Depends(get_letter_service),
):
    """
    Create a cover letter from job title and description.

    - **name**: Job title
    - **description**: Job description
    - **source_id**: Source ID of the CV in the database
    """
    try:
        
        job_requirements = (
            name + "\n" + description
        )
        # Generate cover letter using found requirements and CV data
        letter_content = await letter_service.generate_cover_letter(job_requirements, source_id)

        if letter_content.startswith("Ошибка") or letter_content.startswith("Не найдены"):
            raise HTTPException(status_code=500, detail=letter_content)

        result = {
            "letter_content": letter_content,
            "source_id": source_id,
        }

        return LetterResponse(
            success=True,
            message="Cover letter generated successfully from text",
            data=result
        )

    except Exception as e:
        logging.error("Error uploading CV", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/text/stream")
async def stream_letter_from_text(
    user:CurrentUser,
    name: str = Form(..., min_length=1, max_length=100),
    description: str = Form(..., min_length=1),
    lang: Optional[str] = Form(None, max_length=50),
    cover_letter_service: CoverLetterService = Depends(get_cover_letter_service),
):

    return StreamingResponse(
        _sse_wrap(cover_letter_service.stream_by_text(name, description, user.id, lang=lang)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/translate/stream")
async def stream_translate_letter(
    text: str = Form(..., max_length=10_000, description="Letter content to translate"),
    target_language: str = Form(..., max_length=50, description="Target language, e.g. 'Russian'"),
    letter_service: LetterService = Depends(get_letter_service),
):
    return StreamingResponse(
        _sse_wrap(letter_service.stream_translate_letter(text, target_language)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/upload-cv", response_model=CVUploadResponse)
async def upload_cv(
    user:CurrentUser,
    file: UploadFile = File(..., description="PDF file containing the CV/resume"),
    source_id: str = Form(..., description="Unique identifier for the CV source"),
    
    letter_service: LetterService = Depends(get_letter_service),
):
    """
    Upload a CV/resume PDF file to the vector database.

    - **file**: PDF file containing the CV/resume
    - **source_id**: Unique identifier for the CV source (used for later retrieval)
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        # Validate file size (max 10MB)
        file_content = await file.read()
        if len(file_content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(status_code=400, detail="File size must be less than 10MB")

        # Save file temporarily
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            await letter_service.add_cv(
                user_id=user.id,
                pdf_path=temp_file_path,
                source_id=source_id,
                filename=file.filename,
                original_filename=file.filename,
                file_size=len(file_content),
                content_type=file.content_type or "application/pdf"
            )

            return CVUploadResponse(
                success=True,
                message=f"CV uploaded successfully with source_id: {source_id}",
                source_id=source_id,
                data={
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "source_id": source_id
                }
            )

        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logging.error("Error uploading CV", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading CV: {str(e)}")
