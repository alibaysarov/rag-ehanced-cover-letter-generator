from langchain_openai import ChatOpenAI
from app.services.llm.general import GeneralLLMClient
from langchain_core.prompts import ChatPromptTemplate


class OpenAiClient(GeneralLLMClient):
    def __init__(self):
        model = ChatOpenAI(model="gpt-4o", temperature=0.7, max_completion_tokens=2000)
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
        - Используй keywords из вакансии (под ATS)
        - Не используй эмодзи
        - Избегай общих фраз и клише
        - {language_instruction} Объём 200-300 слов.
        """

        return ChatPromptTemplate.from_messages([
            ("system", "Ты — профессиональный HR-специалист. Пиши сопроводительное письмо строго на языке вакансии."),
            ("human", human),
        ])
    