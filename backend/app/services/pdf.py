from dotenv import load_dotenv
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PDFReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import CVChunkRepository
from app.repository.cv_repository import CVRepository

load_dotenv()


class PdfService:
    def __init__(self, session: AsyncSession = None):
        self.reader = PDFReader()
        self.splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=0)
        self.session = session
        self.cv_repository = CVRepository(session) if session else None
        self.cv_chunk_repository = CVChunkRepository(session) if session else None

    async def upsert_chunks(
        self,
        pdf_path: str,
        source_id: str,
        user_id: int,
    ) -> int:
        """Load and store CV chunks in PostgreSQL for text search."""
        text_chunks = self._load_and_chunk_pdf(pdf_path)
        if not self.cv_chunk_repository:
            return len(text_chunks)
        return await self.cv_chunk_repository.replace_chunks(
            user_id=user_id,
            source_id=source_id,
            chunks=text_chunks,
        )

    async def parse_cv(
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
    ):
        """Parses and stores CV chunks in PostgreSQL."""
        await self.upsert_chunks(pdf_path, source_id, user_id)
        if self.session:
            await self.session.commit()

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
    ):
        """Stores CV chunks and metadata in PostgreSQL."""
        await self.upsert_chunks(pdf_path, source_id, user_id)

        # Save CV metadata to PostgreSQL if repository is available
        if self.cv_repository:
            existing_cv = await self.cv_repository.get_cv_by_source_id(
                source_id=source_id
            )
            if existing_cv is None:
                await self.cv_repository.create_cv(
                    user_id=user_id,
                    source_id=source_id,
                    filename=filename or pdf_path.split("/")[-1],
                    original_filename=original_filename or filename,
                    file_path=pdf_path,
                    file_size=file_size,
                    content_type=content_type,
                    upload_ip=upload_ip,
                    user_agent=user_agent,
                )
            else:
                await self.session.commit()

    def _load_and_chunk_pdf(self, path: str):
        docs = self.reader.load_data(file=path)
        texts = [d.text for d in docs if getattr(d, "text", None)]
        chunks = []
        for t in texts:
            chunks.extend(self.splitter.split_text(t))
        return chunks
