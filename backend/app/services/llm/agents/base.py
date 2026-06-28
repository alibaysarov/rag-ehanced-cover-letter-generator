# from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from abc import ABC, abstractmethod
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents.structured_output import ToolStrategy
from langchain_core.runnables import Runnable
from langchain_core.agents import AgentAction, AgentFinish, AgentStep
import asyncio
from typing import Union

from ..general import GeneralLLMClient

AgentStreamChunk = Union[
    dict[str, list[AgentAction]],   # {"actions": [...]}
    dict[str, list[AgentStep]],     # {"steps": [...]}
    dict[str, str],                 # {"output": "..."}
]

class BaseAiAgent(ABC):

    def __init__(self,prompt_service: GeneralLLMClient):
        self.prompt_service = prompt_service

    @property
    @abstractmethod
    def prompt_template(self) -> ChatPromptTemplate:
        """Наследники возвращают ChatPromptTemplate"""
        ...

    @abstractmethod
    def get_structured_output(self) -> type:
        ...

    @abstractmethod
    def get_tools(self)->list[BaseTool]:
        return []


    def get_agent(self)->Runnable[dict, Union[AgentAction, AgentFinish]]:
        model = self.prompt_service.get_model

        return create_agent(
            model=model,
            tools=self.get_tools(),
            response_format=ToolStrategy(self.get_structured_output())
        )

    def execute(self, body: dict) -> Union[AgentAction, AgentFinish]:
        messages = self.prompt_template().format_messages(**body)
        return self.get_agent().invoke({"messages": messages})

    async def stream(self, body: dict):
        messages = self.prompt_template().format_messages(**body)
        chunks = await asyncio.to_thread(list, self.get_agent().stream({"messages": messages}))
        for chunk in chunks:
            yield chunk