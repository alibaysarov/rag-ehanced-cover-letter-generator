from typing import AsyncIterator, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.base import BaseMessage

from langchain_core.prompts import ChatPromptTemplate
from abc import ABC, abstractmethod

import traceback

'''
@property
    def prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            ("system", "You are a professional translator. Translate to {language}."),
            ("human", "{text}"),
        ])

'''

class GeneralLLMClient(ABC):
    model:BaseChatModel = None
    def __init__(self,model:BaseChatModel):
        schema = self.get_schema()
        if schema is None:
            self.model = model
        else:
            self.model = model.with_structured_output(schema=schema)
        
    
    
    
    
    @property
    def get_model(self):
        return self.model
    
    @property
    @abstractmethod
    def prompt_template(self) -> ChatPromptTemplate:
        """Наследники возвращают ChatPromptTemplate"""
        ...
    
    @abstractmethod
    def get_schema(self)->Optional[type[BaseModel]]:
        """Для настройки structured output"""
        ...
    
    def get_prompt(self, body: dict) -> list[BaseMessage]:
        # Подставляем переменные из body в шаблон
        return self.prompt_template.format_messages(**body)
    
    def set_output(self, schema: Optional[type[BaseModel]] = None) -> None:
        if schema is not None:
            self.model = self.model.with_structured_output(schema=schema)
    
    
    async def get_stream_response(self,body:dict={})-> AsyncIterator[str]:
        messages = self.get_prompt(body)
        async for chunk in self.model.astream(messages):
                if chunk.content:
                    yield chunk.content
    
    
        