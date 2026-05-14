
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import os

from .mistral import MistralClient

from app.schemas.llm_outputs.job_requirements import JobRequirement
from ...schemas.llm_outputs.cv_parse import CVImportModel

class JobParsePrompt(MistralClient):
    def get_schema(self):
        return JobRequirement
    
    @property
    def prompt_template(self):
        human = """
        Отвечай на языке на котором пришел  вакансия
        Проанализируй текст вакансии по: {job_text}
        Извлеки следующую информацию:
        - Название вакансии
        - Название/область проекта
        - Требуемые навыки и компетенции
        Представь информацию в структурированном виде.
        """
        
        
        #
        return ChatPromptTemplate.from_messages([
            ("system", "Ты Hr специалист."),
            ("human", human),
        ])
        


class CVImportPrompt(MistralClient):
    
    # def __init__(self):
    #     base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
    #     model = ChatOllama(model="mistral:7b",format="json", temperature=0, base_url=base_url)
    #     self.model = model
    
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
    
    
    # @property
    # def prompt_template(self):
    #     human = """
    #     Проанализируй текст резюме: {cv_text}
    #     Извлеки и суммируй следующую информацию:
    #     - Имя в резюме
    #     - Фамилия в резюме
    #     - Email (Если есть) в резюме
    #     - Проекты
    #     Представь информацию в структурированном виде.
    #     """

    #     return ChatPromptTemplate.from_messages([
    #         ("system", "You are a professional HR specialist."),
    #         ("human", human),
    #     ])