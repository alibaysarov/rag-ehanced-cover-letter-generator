import logging
from datetime import datetime

from app.repository.cv_chunk_repository import CVChunkRepository
from app.repository.cv_repository import CVRepository

from .pdf import PdfService

logger = logging.getLogger(__name__)


class CVService:
    def __init__(self, repo: CVRepository):
        self.repo = repo
        self.chunk_repo = CVChunkRepository(repo.session)
        self.pdf_service = PdfService(repo.session)

    async def import_cv(
        self,
        user_id: int,
    ):
        pass

    async def add_cv(
        self,
        user_id: int,
        pdf_path: str,
        source_id: str,
        filename: str = None,
        original_filename: str = None,
        file_size: int = 0,
        content_type: str = "application/pdf",
        upload_ip: str = None,
        user_agent: str = None,
    ) -> None:
        await self.pdf_service.add_cv(
            user_id=user_id,
            pdf_path=pdf_path,
            source_id=source_id,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            upload_ip=upload_ip,
            user_agent=user_agent,
        )

    async def get_cvs_by_user(self, user_id: int):
        """
        Get all CVs as options for a user.
        :param user_id: id of user
        :type user_id: int
        """
        result = await self.repo.get_cvs_options_by_user_id(user_id)
        return result

    async def update_cv(
        self,
        cv_id: int,
        pdf_path: str,
        source_id: str,
        filename: str = None,
        original_filename: str = None,
        file_size: int = 0,
        content_type: str = "application/pdf",
        upload_ip: str = None,
        user_agent: str = None,
    ) -> None:
        """
        Обновляет метаданные CV в базе данных

        Args:
            cv_id: ID CV для обновления
            pdf_path: Путь к PDF файлу резюме
            source_id: Уникальный ID источника
            filename: Имя файла
            original_filename: Оригинальное имя файла
            file_size: Размер файла в байтах
            content_type: MIME тип файла
            upload_ip: IP адрес загрузки
            user_agent: User agent браузера
        """
        cv = await self.repo.get_cv_by_id(cv_id)
        if not cv:
            raise ValueError(f"CV with id {cv_id} not found")
        current_source_id = cv.source_id
        try:
            data = {
                "source_id": source_id,
                "filename": filename or cv.filename,
                "original_filename": original_filename or cv.original_filename,
                "file_path": pdf_path or cv.file_path,
                "file_size": file_size or cv.file_size,
                "content_type": content_type or cv.content_type,
                "upload_ip": upload_ip or cv.upload_ip,
                "user_agent": user_agent or cv.user_agent,
                "updated_at": datetime.now(),
            }
            await self.repo.update_cv(cv, data)
            if str(current_source_id) != str(source_id):
                await self.chunk_repo.delete_by_source_id(current_source_id)
            await self.chunk_repo.replace_chunks(
                user_id=cv.user_id,
                source_id=source_id,
                chunks=self.pdf_service._load_and_chunk_pdf(pdf_path),
            )
            await self.repo.session.commit()
        except Exception as e:
            logger.error("Error updating CV", exc_info=True)
            await self.repo.session.rollback()
            raise e

    async def get_by_user(self, user_id: int):
        """
        Get all CVs for a user.
        :param user_id: id of user
        :type user_id: int
        """
        result = await self.repo.get_cvs_by_user_id(user_id)
        return result

    async def delete_cv(self, cv_id: int):
        """
        Delete CV by id with rollback support.
        :param cv_id: id of CV
        :type cv_id: int
        """
        cv = await self.repo.get_cv_by_id(cv_id)
        if not cv:
            raise ValueError(f"CV with id {cv_id} not found")

        source_id = cv.source_id

        try:
            await self.chunk_repo.delete_by_source_id(source_id)
            await self.repo.delete_cv(cv)
            await self.repo.session.commit()

        except Exception as e:
            logger.error("Error deleting CVs", exc_info=True)
            await self.repo.session.rollback()

            raise Exception(f"Failed to delete CV: {str(e)}")
