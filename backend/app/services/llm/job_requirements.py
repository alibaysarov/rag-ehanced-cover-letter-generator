
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import os

from .qwen import QwenClient
from .gemini import GeminiClient
from app.schemas.llm_outputs.job_requirements import JobRequirement
from ...schemas.llm_outputs.cv_parse import CVImportModel
from .small_llm import SmallLLMClient
class JobParsePrompt(SmallLLMClient):
    def get_schema(self):
        return JobRequirement

    @property
    def prompt_template(self):
        system="""
            Вытащи эти данные из текста в виде json
            id=id вакансии
            name=название вакансии
            technologies = Список технологий
        """
        
    
        human = """
            {job_text}
        """

        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", human),
        ])
        


class CVImportPrompt(QwenClient):

    
    def get_schema(self):
        return CVImportModel
    
    
    @property
    def prompt_template(self):
        system = """Ты извлекаешь структурированные данные из резюме в JSON.

            ПРАВИЛА (строго):
            - Каждое место работы = ОТДЕЛЬНЫЙ объект в массиве projects.
            - В CV обычно 2-6 мест работы — внимательно посчитай блоки с датами.
            - email: если в тексте нет валидного email (с символом @), возвращай ровно null. Не пиши плейсхолдеры.
            - skills = что человек УМЕЕТ делать (например: "проектирование REST API", "оптимизация SQL-запросов").
            - achievements = что он СДЕЛАЛ, с метриками если есть (например: "ускорил импорт Excel с 60с до 300мс").
            - technologies = ТОЛЬКО названия инструментов: языки, БД, фреймворки, сервисы (например: "Node.js", "Redis", "Docker"). Одна технология на один элемент
            - Никогда не клади в technologies: даты, должности, целые предложения, описания работы."""
        human = """Пример входа:
            ---
            john_simth@gmail.com
            John Smith
            Acme Corp, March 2022 - Present
            Senior Developer
            - Built payment API handling 10k requests/sec
            - Reduced latency by 40%
            Stack: Go, PostgreSQL, Kafka, Docker
            ---

            Пример выхода:
            {{
            "first_name": "John",
            "last_name": "Smith",
            "email": john_simth@gmail.com,
            "projects": [
                {{
                "name": "Acme Corp",
                "skills": ["проектирование высоконагруженных API", "оптимизация производительности"],
                "achievements": ["Построил платёжный API на 10k req/sec", "Снизил latency на 40%"],
                "technologies": ["Go", "PostgreSQL", "Kafka", "Docker"]
                }}
            ]
            }}

            Теперь обработай это резюме:
            ---
            {cv_text}
            ---"""

        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", human),
        ])