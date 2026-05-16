
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
        system = """Ты HR-специалист. Извлекаешь из текста вакансии структурированные данные в JSON.

ПРАВИЛА КЛАССИФИКАЦИИ ТЕХНОЛОГИЙ:
Раздели технологии вакансии на ТРИ непересекающихся ведра:

- required_technologies — явно обязательные. Маркеры в тексте: "требуется", "обязательно", "необходимо знание", "опыт работы с", "уверенные знания", основной тех-стек в заголовке/первых строках требований.
- preferred_technologies — желательные. Маркеры: "будет плюсом", "приветствуется", "опыт с ... преимущество", "желательно".
- nice_to_have_technologies — опциональные. Маркеры: "знакомство с", "понимание основ", "опционально", "nice to have".

ОБЯЗАТЕЛЬНО:
- Все названия — в нижнем регистре, одна технология = один элемент.
- Не дублируй технологию между ведрами.
- Если категория неоднозначна — клади в preferred_technologies.
- В ведра кладёшь ТОЛЬКО названия инструментов: языки, БД, фреймворки, сервисы, протоколы. Не клади целые фразы, должности, методологии без инструмента."""

        human = """Пример входа:
---
Backend-разработчик (Node.js)

Требования:
- Уверенные знания Node.js, PostgreSQL, REST API
- Опыт работы с Redis обязателен
- Будет плюсом: опыт с Kafka, знание TypeScript
- Желательно знакомство с Docker
---

Пример выхода:
{{
  "name": "Backend-разработчик (Node.js)",
  "lang": "RU",
  "project_name": "Backend-разработка",
  "required_technologies": ["node.js", "postgresql", "rest api", "redis"],
  "preferred_technologies": ["kafka", "typescript"],
  "nice_to_have_technologies": ["docker"],
  "requirements": ["Уверенные знания Node.js, PostgreSQL, REST API", "Опыт работы с Redis обязателен", "Будет плюсом: опыт с Kafka, знание TypeScript", "Желательно знакомство с Docker"]
}}

Отвечай на языке, на котором написана вакансия (поле lang заполни кодом языка: RU, EN и т.п.).

Теперь обработай эту вакансию:
---
{job_text}
---"""

        return ChatPromptTemplate.from_messages([
            ("system", system),
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