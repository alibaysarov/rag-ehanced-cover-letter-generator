from .qwen import QwenClient
from .gemini import GeminiClient
from app.schemas.llm_outputs.relevant_projects import RelevantProjects
from langchain_core.prompts import ChatPromptTemplate

from langchain_ollama import ChatOllama
import os

_MODEL = "qwen2.5:0.5b"
class RelevantProjectsPrompt(QwenClient):
    
    def __init__(self):
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = ChatOllama(model=_MODEL, temperature=0.1,reasoning=False,num_ctx=4096, base_url=base_url)
        
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