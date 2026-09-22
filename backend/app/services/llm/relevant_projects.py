from langchain_core.prompts import ChatPromptTemplate

from app.schemas.llm_outputs.relevant_projects import RelevantProjects

from .factory import create_chat_model
from .general import GeneralLLMClient


class RelevantProjectsPrompt(GeneralLLMClient[RelevantProjects]):
    def __init__(self):
        super().__init__(model=create_chat_model(temperature=0.1))

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

        return ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", human),
            ]
        )
