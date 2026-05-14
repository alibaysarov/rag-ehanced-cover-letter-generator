from openai import OpenAI, AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.pdf import PdfService
from app.schemas.rag import RAGSearchResult
from app.storage.repository.qdrant import QdrantStorage
from app.repository.cv_repository import CVRepository
from app.repository.letter_repository import LetterRepository
from typing import AsyncGenerator
from app.services.llm.open_ai import OpenAiClient
from app.services.llm.mistral import MistralClient
from app.services.llm.agents.job_requirement import JobRequirementAgent

class LetterService():
    def __init__(self, session: AsyncSession = None):
        self.client = OpenAI()
        # self.llm = OpenAiClient()
        self.llm = MistralClient()
        self.job_requirement_agent = JobRequirementAgent()
        self.async_client = AsyncOpenAI()
        self.storage = QdrantStorage()
        
        self.session = session
        self.pdf_service = PdfService(session)
        self.cv_repository = CVRepository(session) if session else None
        self.letter_repository = LetterRepository(session) if session else None

    async def search_job_requirements(self, job_title: str, company: str = None) -> str:
        """
        Ищет требования для вакансии используя OpenAI с web_search_preview tool

        Args:
            job_title: Название вакансии
            company: Название компании (опционально)

        Returns:
            str: Требования к вакансии в текстовом формате
        """
        search_query = f"требования к вакансии {job_title}"
        if company:
            search_query += f" в компании {company}"

        messages = [
            {
                "role": "user",
                "content": f"Найди и суммируй основные требования и обязанности для вакансии '{job_title}'{' в компании ' + company if company else ''}. Используй поиск в интернете для получения актуальной информации."
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=messages,
                max_tokens=800,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Ошибка при поиске требований: {str(e)}"

    async def generate_cover_letter(self, job_requirements: str, source_id: int) -> str:
        """
        Генерирует сопроводительное письмо на основе требований вакансии и данных из резюме

        Args:
            job_requirements: Требования к вакансии (полученные из search_job_requirements)
            source_id: ID источника резюме в базе данных

        Returns:
            str: Сгенерированное сопроводительное письмо
        """
        

        # Получаем ключевые навыки и опыт из резюме
        skills_query = "ключевые навыки опыт образование достижения"
        resume_data = self.__search_resume_data(skills_query,source_id=source_id)
        

        if not resume_data.contexts:
            return "Не найдены данные резюме в базе данных. Сначала загрузите свое резюме."

        # Формируем контекст из резюме
        resume_context = "\n\n".join(f"- {c}" for c in resume_data.contexts)

        prompt = f"""
       Ты - помощник по созданию профессиональных сопроводительных писем.

        У тебя есть:
        1. Требования к вакансии: {job_requirements}
        2. Данные из резюме кандидата: {resume_context}
    Задача: на основе этих данных сгенерировать персонализированное сопроводительное письмо, которое
        Показывает почему мой предыдущий опыт поможет в их работе 
        Имеет ключевые слова из резюме
        Сопоставь (там где это максимально корректно) кейсы из моего релевантного опыта  к требованиям в вакансии, но так чтобы технологии соответствовали по смыслу
        Пиши в профессиональном, но дружелюбном тоне
        Избегай общих фраз и клише
        Письмо должно быть на том языке, на котором написаны требования для вакансии. Объемом 200-300 слов.
    """
    

        try:
            response = self.client.responses.create(
                model="gpt-4o",
                max_output_tokens=2048,
                input=prompt,
                temperature=1.0
            )
            
            letter_content = response.output_text
            return letter_content

        except Exception as e:
            return f"Ошибка при генерации сопроводительного письма: {str(e)}" 

    async def stream_cover_letter(
        self, job_requirements: str, source_id: int, target_language: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams cover letter tokens.
        Yields raw text deltas (caller wraps in SSE frame).
        Raises ValueError if no resume data found.
        """

        skills_query = "ключевые навыки опыт образование достижения"
        resume_data = self.__search_resume_data(skills_query,source_id=source_id)

        if not resume_data.contexts:
            raise ValueError("Не найдены данные резюме в базе данных.")

        resume_context = "\n\n".join(f"- {c}" for c in resume_data.contexts)

        language_instruction = (
            f"Письмо должно быть написано строго на {target_language}."
            if target_language
            else "Письмо должно быть русском языке."
        )

        body = {
            "job_requirements": job_requirements,
            "resume_context":resume_context,
            "language_instruction":language_instruction
        }

        async for delta in self.llm.get_stream_response(body):
            yield delta

    async def stream_translate_letter(
        self, text: str, target_language: str
    ) -> AsyncGenerator[str, None]:
        """
        Translates an existing cover letter into target_language, streaming tokens.
        Raises ValueError for empty input.
        """
        if not text.strip():
            raise ValueError("Cannot translate empty text.")

        system_prompt = (
            "You are a professional translator specialising in business correspondence. "
            "Translate the provided cover letter into "
            f"{target_language}. "
            "Preserve all formatting, paragraph breaks, and professional tone. "
            "Output only the translated letter — no explanations or metadata."
        )

        async with self.async_client.chat.completions.stream(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            max_tokens=2048,
            temperature=0.3,
        ) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

    async def stream_by_url(
        self, job_url: str, source_id: int, target_language: str | None = None
    ) -> AsyncGenerator[str, None]:
        """
        Phase 1: silently accumulate job requirements from URL.
        Phase 2: stream cover letter generation.
        Yields raw text deltas and status sentinels.
        """
        yield "__PARSING__"

        # prompt = self.__get_job_requirements_prompt(job_url=job_url)
        # job_requirements = await self.__fetch_job_requirements(prompt)
        job_requirements = await self.__fetch_job_requirements_by_agent({
            "job_url":job_url
        })
        print("reqs are ",job_requirements)
        if not job_requirements:
            raise ValueError("Не удалось извлечь требования из URL.")

        yield "__READY__"

        async for delta in self.stream_cover_letter(job_requirements, source_id, target_language):
            yield delta
        
    async def parse_cv(self,user_id: int,pdf_path: str, source_id: str, filename: str = None,
                    original_filename: str = None,
                    file_size: int = 0, content_type: str = "application/pdf",
                    upload_ip: str = None, user_agent: str = None):
        await self.pdf_service.parse_cv(
            user_id=user_id,
            pdf_path=pdf_path,
            source_id=source_id,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            upload_ip=upload_ip,
            user_agent=user_agent
        )

    async def add_cv(self, user_id: int, pdf_path: str, source_id: str, filename: str = None,
                    original_filename: str = None, file_size: int = 0, content_type: str = "application/pdf",
                    upload_ip: str = None, user_agent: str = None):
        """
        Загружает CV в векторную базу данных и сохраняет метаданные в PostgreSQL

        Args:
            user_id: ID пользователя, которому принадлежит CV
            pdf_path: Путь к PDF файлу резюме
            source_id: Уникальный ID источника
            filename: Имя файла
            original_filename: Оригинальное имя файла
            file_size: Размер файла в байтах
            content_type: MIME тип файла
            upload_ip: IP адрес загрузки
            user_agent: User agent браузера
        """
        await self.pdf_service.add_cv(
            user_id=user_id,
            pdf_path=pdf_path,
            source_id=source_id,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            content_type=content_type,
            upload_ip=upload_ip,
            user_agent=user_agent
        )
    

    async def generate_by_url(self, job_url: str, source_id: int) -> str:
        """
        Генерирует сопроводительное письмо на основе URL вакансии и данных из резюме

        Args:
            job_url: URL страницы с вакансией
            source_id: ID источника резюме в базе данных

        Returns:
            str: Сгенерированное сопроводительное письмо
        """
        # Шаг 1: Парсим требования из URL вакансии
        job_requirements = await self._parse_job_requirements_from_url(job_url)
        if not job_requirements or job_requirements.startswith("Ошибка"):
            return job_requirements

        # Шаг 2: Получаем данные из резюме и генерируем письмо
        return await self.generate_cover_letter(job_requirements, source_id)

    def __get_letter_prompt(self,job_requirements:str,resume_context:str,language_instruction:str)->str:
        prompt = f"""
        Ты - помощник по созданию профессиональных сопроводительных писем.

        У тебя есть:
        1. Требования к вакансии: {job_requirements}
        2. Данные из резюме кандидата: {resume_context}
        Задача: на основе этих данных сгенерировать персонализированное сопроводительное письмо, которое
        Показывает почему мой предыдущий опыт поможет в их работе 
        Имеет ключевые слова из резюме
        Сопоставь (там где это максимально корректно) кейсы из моего релевантного опыта  к требованиям в вакансии, но так чтобы технологии соответствовали по смыслу
        Пиши в профессиональном, но дружелюбном тоне
        Избегай общих фраз и клише
        {language_instruction} Объемом 200-300 слов.
        """
        return prompt

    def __search_resume_data(self,query: str,source_id, top_k: int = 10)->RAGSearchResult:
            """
            Ищем релевантные данные из резюме в векторной базе
            """
            
            query_vec = self.pdf_service.embed_texts([query])[0]
            found = self.storage.search(query_vector=query_vec, top_k=top_k)
            filtered_contexts = []
            filtered_sources = []
            for context, source in zip(found["contexts"], found["sources"]):
                if str(source.get("source_id")) == str(source_id):
                    filtered_contexts.append(context)
                    filtered_sources.append(source)
            return RAGSearchResult(contexts=filtered_contexts, sources=filtered_sources)
    
    
    def __get_job_requirements_prompt(self,job_url:str):
        prompt = f"""
        Проанализируй страницу вакансии по URL: {job_url}
        Затем пиши на том языке, на котором информация на странице вакансии.
        Извлеки и суммируй следующую информацию:
        - Название вакансии
        - Основные обязанности
        - Требуемые навыки и компетенции
        - Требуемый опыт работы
        - Образование и квалификация
        - Дополнительные требования

        Представь информацию в структурированном виде.
        """
        return prompt

    async def __fetch_job_requirements_by_agent(self, body: dict) -> str:
        parts: list[str] = []
        async for chunk in self.job_requirement_agent.stream(body):
            if "output" in chunk:
                result = chunk["output"]
                parts.append(result.requirements)
                # return "\n".join(result.requirements)
        return "".join(parts)

    async def __fetch_job_requirements(self, prompt: str) -> str:
        parts: list[str] = []
        async with self.async_client.responses.stream(
            model="gpt-4.1-mini",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        ) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    parts.append(event.delta)
        return "".join(parts)

    async def _parse_job_requirements_from_url(self, job_url: str) -> str:
        """
        Парсит требования к вакансии из URL страницы

        Args:
            job_url: URL страницы с вакансией

        Returns:
            str: Извлеченные требования к вакансии
        """
        prompt = f"""
        Проанализируй страницу вакансии по URL: {job_url}
        Затем пиши на том языке, на котором информация на странице вакансии.
        Извлеки и суммируй следующую информацию:
        - Название вакансии
        - Основные обязанности
        - Требуемые навыки и компетенции
        - Требуемый опыт работы
        - Образование и квалификация
        - Дополнительные требования

        Представь информацию в структурированном виде.
        """

        try:
            response = self.client.responses.create(
                model="gpt-4.1-mini",
                tools=[{ "type": "web_search_preview" }],
                input=prompt
            )
            return response.output_text

        except Exception as e:
            print(e)
            return f"Ошибка при парсинге URL вакансии: {str(e)}"