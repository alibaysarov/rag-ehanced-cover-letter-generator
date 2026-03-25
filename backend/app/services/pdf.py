import time
from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from app.storage.repository.qdrant import QdrantStorage
from app.repository.cv_repository import CVRepository

load_dotenv()

EMBED_MODEL="text-embedding-3-large"
EMBED_DIM=3072

class PdfService():
    def __init__(self, session: AsyncSession = None):
        self.reader = PDFReader()
        self.client = OpenAI()
        self.storage = QdrantStorage()
        self.splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=0)
        self.session = session
        self.cv_repository = CVRepository(session) if session else None

    def upsert_vectors(self,pdf_path:str,original_filename: str,source_id:str,user_id:int):
        """Embedding pdf файла и upsert в векторную БД."""
        text_chunks = self._load_and_chunk_pdf(pdf_path)
        vectors = self.embed_texts(text_chunks)
        ids = [abs(hash(f"{original_filename}_{source_id}_{i+1}")) for i in range(len(text_chunks))]
        payloads = [
            {
                "user_id":user_id,
                "text": chunk,
                "source": pdf_path,
                "source_id": source_id,
                "chunk_index": i
            }
            for i, chunk in enumerate(text_chunks)
        ]
        self.storage.upsert(ids=ids, vectors=vectors, payloads=payloads)

    async def add_cv(self, user_id: int, pdf_path: str, source_id: str, filename: str = None,
                    original_filename: str = None, file_size: int = 0, content_type: str = "application/pdf",
                    upload_ip: str = None, user_agent: str = None):
        """Загружает CV в векторную БД и сохраняет метаданные в PostgreSQL"""
        self.upsert_vectors(pdf_path, original_filename or filename, source_id, user_id)

        # Save CV metadata to PostgreSQL if repository is available
        if self.cv_repository:
            existing_cv = await self.cv_repository.get_cv_by_source_id(source_id=source_id)
            if existing_cv is None:
                await self.cv_repository.create_cv(
                    user_id=user_id,
                    source_id=source_id,
                    filename=filename or pdf_path.split('/')[-1],
                    original_filename=original_filename or filename,
                    file_path=pdf_path,
                    file_size=file_size,
                    content_type=content_type,
                    upload_ip=upload_ip,
                    user_agent=user_agent
                )

    def _load_and_chunk_pdf(self,path:str):
        docs = self.reader.load_data(file=path)
        texts = [d.text for d in docs if getattr(d,"text",None)]
        chunks = []
        for t in texts:
            chunks.extend(self.splitter.split_text(t))
        return chunks
    
    def embed_texts(self,texts:list[str])-> list[list[float]]:
        response =self.client.embeddings.create(
            model=EMBED_MODEL,
            dimensions=EMBED_DIM,
            input=texts
        )
        return [item.embedding for item in response.data]