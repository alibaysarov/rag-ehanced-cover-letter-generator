from langchain_ollama import ChatOllama

from app.core.config import settings
from app.services.llm.general import GeneralLLMClient

_MODEL = "json-parser:latest"


class SmallLLMClient(GeneralLLMClient):
    def __init__(self):

        base_url = settings.OLLAMA_HOST

        model = ChatOllama(
            model=_MODEL,
            format="json",
            num_ctx=4096,
            temperature=0.1,
            num_predict=400,
            reasoning=False,
            base_url=base_url,
        )
        super().__init__(model=model)

    def get_schema(self):
        return None
