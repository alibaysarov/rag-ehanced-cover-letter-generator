import logging
from datetime import datetime

from requests import session
from app.repository.cv_repository import CVRepository
from app.storage.repository.qdrant import QdrantStorage
from qdrant_client.models import PointStruct

from app.services.pdf import PdfService

logger = logging.getLogger(__name__)

class CVService():
    def __init__(self,repo:CVRepository):
        self.repo = repo
        self.storage = QdrantStorage()
        repo.session
        self.pdf_service = PdfService(repo.session)
    

    async def get_cvs_by_user(self,user_id:int):
        """
        Get all CVs as options for a user.
        :param user_id: id of user
        :type user_id: int
        """
        result = await self.repo.get_cvs_options_by_user_id(user_id)
        return result
    
    async def update_cv(self,cv_id:int, pdf_path: str, source_id: str, filename: str = None,
                    original_filename: str = None, file_size: int = 0, content_type: str = "application/pdf",
                    upload_ip: str = None, user_agent: str = None) -> None:
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
        backup_points = self._get_points_by_source_id(current_source_id)
        try:
            self._delete_points_by_source_id(current_source_id)
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
            self._upsert_points(pdf_path, original_filename or filename, source_id, cv.user_id)
            self.repo.session.commit()
        except Exception as e:
            logger.error("Error updating CV", exc_info=True)
            # Откатываем БД
            await self.repo.session.rollback()
            # Восстанавливаем данные в Qdrant
            self._restore_points(backup_points)
    
    async def get_by_user(self,user_id:int):
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
        # Получаем CV для source_id
        cv = await self.repo.get_cv_by_id(cv_id)
        if not cv:
            raise ValueError(f"CV with id {cv_id} not found")
        
        source_id = cv.source_id
        
        # Сохраняем данные из Qdrant для возможного отката
        backup_points = self._get_points_by_source_id(source_id)
        
        try:
            # 1. Удаляем из Qdrant
            self._delete_points_by_source_id(source_id)
            
            # 2. Удаляем из БД
            self.repo.delete_cv(cv)
            
            # 3. Коммитим транзакцию БД
            self.repo.session.commit()
            
        except Exception as e:
            logger.error("Error deleting CVs", exc_info=True)
            # Откатываем БД
            self.repo.session.rollback()
            
            # Восстанавливаем данные в Qdrant
            self._restore_points(backup_points)
            
            raise Exception(f"Failed to delete CV: {str(e)}")
        

    def _delete_points_by_source_id(self, source_id: int):
        """Delete all points with given source_id"""
        self.storage.delete_by_source_id(source_id)

    def _upsert_points(self, pdf_path:str,original_filename: str,source_id:str,user_id:int):
        self.pdf_service.upsert_vectors(pdf_path=pdf_path,original_filename=original_filename,source_id=source_id,user_id=user_id)

    def _get_points_by_source_id(self, source_id: int):
        """Get all points for potential rollback"""
        return self.storage.get_points_by_source_id(source_id)
    def _restore_points(self, points):
        """Restore points in Qdrant from backup"""
        if points:
            restored_points = [
                PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=point.payload
                )
                for point in points
            ]
            self.storage.client.upsert(
                collection_name=self.storage.collection,
                points=restored_points
            )
