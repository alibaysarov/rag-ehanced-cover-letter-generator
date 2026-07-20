from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.schemas.llm_outputs.relevant_projects import RelevantProjects

from .general import GeneralLLMClient


class RelevantProjectsPrompt(GeneralLLMClient[RelevantProjects]):
    
    def __init__(self):
        _MODEL = "qwen2.5:0.5b"
        
        model = ChatOllama(model=_MODEL, temperature=0.1,reasoning=False,num_ctx=4096, base_url=settings.OLLAMA_HOST)
        
        self.model = model.with_structured_output(RelevantProjects)
        
    def get_schema(self):
        return RelevantProjects
    @property
    def prompt_template(self):
        system = """
            Есть вакансия и список проектов которые ей подходят.
            верни массив id тех проектов которые под эту вакансию подходят лучше всего.
        """

        human = """Пример входа:
            Вакансия:
            {job_text}
            
            Технологии вакансии:
            {technologies}
            
            Список проектов:
            {projects}

        """

        return ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", human),
        ])