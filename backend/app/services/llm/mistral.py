import os
from langchain_ollama import ChatOllama
from app.services.llm.general import GeneralLLMClient
from langchain_core.prompts import ChatPromptTemplate


class MistralClient(GeneralLLMClient):
    def __init__(self):
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        model = ChatOllama(model="mistral:7b",format="json", temperature=0.7, base_url=base_url)
        super().__init__(model=model)


    def get_schema(self):
        return None

    @property
    def prompt_template(self):
        human = """
        У тебя есть:
        1. Требования к вакансии: {job_requirements}
        2. Данные из резюме кандидата: {resume_context}

        Напиши профессиональное сопроводительное письмо разработчика (Backend/Fullstack/Frontend — подставь по контексту).
        Отклик должен показывать конкурентные преимущества и метрики из предыдущих проектов.

        Ограничения:
        - Пиши про достижения, не про 
        - Используй keywords из вакансии (под ATS)
        - Не используй эмодзи
        - Избегай общих фраз и клише
        - {language_instruction} Объём 200-300 слов.
        """

        return ChatPromptTemplate.from_messages([
            ("system", "You are a professional HR specialist. Write the cover letter in the language of the job requirements."),
            ("human", human),
        ])
