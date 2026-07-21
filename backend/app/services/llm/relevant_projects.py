from langchain_core.prompts import ChatPromptTemplate

from app.schemas.llm_outputs.relevant_projects import RelevantProjects

from .general import GeneralLLMClient
from .models.ollama import OllamaModel


class RelevantProjectsPrompt(GeneralLLMClient[RelevantProjects]):
    def __init__(self):
        _MODEL = "qwen2.5:0.5b"

        model = OllamaModel(
            model=_MODEL,
            temperature=0.1,
            reasoning=False,
            num_ctx=4096,
        )
        super().__init__(model=model.model)

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
