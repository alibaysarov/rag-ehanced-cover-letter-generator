import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from .general import GeneralLLMClient
from .gemini import GeminiClient
from .qwen import QwenClient
from pydantic import BaseModel,Field

_MODEL="qwen2.5:7b"
_GEMINI_MODEL = "gemini-3.5-flash"
# class CoverLetterPrompt(GeneralLLMClient):
# def __init__(self):
#         base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
#         gemini_model = ChatGoogleGenerativeAI(
#             model=_GEMINI_MODEL,
#             temperature=0,
#             max_tokens=4096,
#         )
        
#         ollama_model = ChatOllama(model=_MODEL, temperature=0, base_url=base_url,top_k=5)
#         model = gemini_model.with_fallbacks([ollama_model])
#         super().__init__(model=model)


# "Добрый день меня заинтересовала ваша вакансия. Думаю мой релевантный опыт подойдет под ваши требования и нужды."


'''
Шаг 1 (маленькая модель): классифицируй роль вакансии → "backend"
Шаг 2 (маленькая модель): классифицируй каждый проект → ["backend", "frontend", "backend"]
Шаг 3 (код, не LLM): отфильтруй проекты программно по совпадению категорий
Шаг 4 (код, не LLM): найди пересечение technologies через set intersection
Шаг 5 (LLM, любого размера): сгенерируй текст письма на основе уже отфильтрованных, готовых данных
'''

"""
TECH_CATEGORY_MAP = {
    "react": "frontend", "vue": "frontend", "angular": "frontend", "css": "frontend",
    "node.js": "backend", "express": "backend", "php": "backend", "java": "backend",
    "spring": "backend", ".net": "backend", "django": "backend", "fastapi": "backend",
    "react native": "mobile", "flutter": "mobile", "swift": "mobile", "kotlin": "mobile",
    "docker": "devops", "kubernetes": "devops", "terraform": "devops",
    "pandas": "data", "pytorch": "data", "sql": "data",
}
keywords vector search
"""

"""
1. [код, без LLM] Tech intersection: vacancy_technologies ∩ user_projects.technologies
2. [код, без LLM] Классификация роли вакансии по ключевым словам в названии + технологиям
3. [код, без LLM] Классификация роли каждого проекта по его технологиям  
4. [код, без LLM] Фильтрация: оставить только проекты с role == vacancy_role (или fullstack-правило)
5. [код, без LLM] Ранжирование отфильтрованных проектов по количеству совпадений с vacancy_requirements
   → выбрать top-1 (Проект 1) и top-2 (Проект 2, если пересечение >50%)
6. [LLM, только генерация текста] Промпт содержит УЖЕ готовые данные:
   - готовый Проект 1 с его данными
   - готовый Проект 2 (или пусто)
   - готовое пересечение технологий для секции "Технологии"
   - только инструкции формата, стиля, запрещённых фраз и придумывания реалистичных цифр
"""



class CoverLetterResult(BaseModel):
    content:str = Field(...,description="Текст письма")


# _MODEL="qwen3:1.7b"
_MODEL="qwen2.5:7b"
# _MODEL="qwen3.5:4b"
class CoverLetterPrompt(QwenClient):

    def __init__(self):
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        model = ChatOllama(model=_MODEL,num_ctx=8192,num_predict=1024, temperature=0.1,reasoning=False, base_url=base_url)
        model = model.with_structured_output(CoverLetterResult)
        self.model = model
    def get_schema(self):
        return CoverLetterResult
    
    @property
    def prompt_template(self):

        system_message = """Ты пишешь короткое сопроводительное письмо от лица IT-специалиста.

Пиши от первого лица, на языке из поля lang (если пусто — по-русски).
Не используй **, ---, #, списки с маркерами, квадратные скобки [], слово "Дорогой".

Вот пример готового письма (структуру скопируй, а слова, названия проектов и технологии замени на данные кандидата):

Добрый день! Я работал на таком же проекте как у вас и умею решать такие задачи.

Мои достижения и проекты:

Система учёта заказов для компании "Рога и копыта":
- Разработал REST API для обработки заказов, используя Python и FastAPI.
- Оптимизировал запросы к базе данных, снизив время ответа на 35%.
Стек: Python, FastAPI, PostgreSQL.

Интернет магазин для компании "Рога и копыта":
- Разработал REST API для интернет магазина, используя Java и Spring boot.
- Оптимизировал запросы к базе данных, снизив время ответа на 45%.
Стек: Java, Spring boot, PostgreSQL.
С уважением, Иван Иванов

Правила:
- Название проекта пиши обычным текстом, без квадратных скобок и без двоеточия в конце можно оставить как в примере.
- Числа обязательны в каждом предложении о проекте. Нет данных — придумай реалистичное.
- Технологии в блоке "Стек" бери только из списка технологий вакансии.
- Не пиши "командный игрок", "быстро обучаюсь", "оптимизировал" без числа.
- Если второго проекта в данных нет — не добавляй его.
- Если есть имя и фамилия кандидата — напиши "С уважением, Имя Фамилия". Если имени нет — напиши одно предложение о готовности к интервью вместо подписи.
"""
        
        # system_message = """Ты пишешь короткое сопроводительное письмо от лица IT-специалиста.

        #     Пиши от первого лица, на языке из поля lang (если пусто — по-русски).
        #     Не используй **, ---, #, списки с маркерами, слово "Дорогой".

        #     Строго скопируй этот шаблон и заполни [квадратные скобки]:

        #     Добрый день! Я работал на таком же проекте как у вас и умею решать такие задачи.

        #     Мои достижения и проекты:

        #     [Название проекта]:
        #     - [что сделал], используя [технология из списка технологий вакансии]. 
        #     - [Второе предложение с результатом — используй число, например RPS, мс или % прироста]. 
        #     Стек: [2-3 технологии из списка технологий вакансии].

            
        #     [Если есть имя и фамилия — напиши "С уважением, Имя Фамилия". Если имени нет — напиши одно предложение о готовности к интервью.]

        #     Правила:
        #     - Числа обязательны в каждом предложении о проекте. Нет данных — придумай реалистичное.
        #     - Технологии в блоке "Стек" бери только из списка технологий вакансии.
        #     - Не пиши "командный игрок", "быстро обучаюсь", "оптимизировал" без числа.
        #     - Финальное письмо - без квадратных скобок
        #     """
        human_message = """Имя: {user_first_name} {user_last_name}
            Язык: {lang}
            Вакансия: {name}
            Технологии вакансии: {vacancy_technologies}
            Требования вакансии: {vacancy_requirements}

            Мои проекты:
            {user_projects}

            Напиши письмо по шаблону выше.
        """
        
        return ChatPromptTemplate.from_messages([system_message,human_message])