from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel,Field
from .base import BaseAiAgent
from ..mistral import MistralClient
from .tools.fetch_url import fetch_webpage,parse_hh


class JobRequirements(BaseModel):
    name: str = Field("Название вакансии")
    project_name: str = Field("Название/область проекта")
    requirements: list[str] = Field("Требуемые навыки и компетенции")


class JobRequirementAgent(BaseAiAgent):
    
    def __init__(self):
        prompt_service = MistralClient()
        super().__init__(prompt_service)
    
    
    def get_structured_output(self):
        return JobRequirements
    
    def get_tools(self):
        # search_tool = DuckDuckGoSearchRun()
        return [parse_hh]
    
    def prompt_template(self):
        # human = """
        
        # Проанализируй страницу вакансии по URL: {job_url}
        # ипользуй parse_hh для получения текста страницы
        
        # Затем пиши на том языке, на котором информация на странице вакансии.
        # Извлеки и суммируй следующую информацию:
        # - Название вакансии
        # - Требуемые навыки и компетенции
        # Представь информацию в структурированном виде.
        # """
        
        human = """
        
        Проанализируй текст вакансии по: {job_text}
        
        Затем пиши на том языке, на котором информация на странице вакансии.
        Извлеки и суммируй следующую информацию:
        - Название вакансии
        - Требуемые навыки и компетенции
        Представь информацию в структурированном виде.
        """

        return ChatPromptTemplate.from_messages([
            ("system", "You are a professional HR specialist."),
            ("human", human),
        ])