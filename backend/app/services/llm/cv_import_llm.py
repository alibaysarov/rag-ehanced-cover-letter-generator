from mistral import MistralClient
from langchain_core.prompts import ChatPromptTemplate

from backend.app.schemas.llm_outputs.cv_parse import CVImportModel
class CVImportPrompt(MistralClient):
    
    
    def get_schema(self):
        return CVImportModel
    
    @property
    def prompt_template(self):
        human = """
        У тебя есть Текст резюме: твоя задача вытащить из него проекты а в проекте должно быть
        - название (name)
        -навыки skills
        - достижения achievements
        - используемые технологии (technologies) 
        {cv_text}
        """

        return ChatPromptTemplate.from_messages([
            ("system", "You are a professional HR specialist. Write the cover letter in the language of the job requirements."),
            ("human", human),
        ])