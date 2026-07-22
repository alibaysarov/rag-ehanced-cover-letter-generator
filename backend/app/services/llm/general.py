from abc import ABC, abstractmethod
from typing import AsyncIterator, Generic, Optional, TypeVar, Union, cast

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.base import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class GeneralLLMClient(ABC, Generic[SchemaT]):
    model: BaseChatModel = None

    def __init__(self, model: BaseChatModel):
        schema = self.get_schema()
        self._schema = schema  # сохраняем схему как атрибут
        if self._schema is None:
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
    def get_schema(self) -> Optional[type[SchemaT]]: ...

    def get_prompt(self, body: dict) -> list[BaseMessage]:
        # Подставляем переменные из body в шаблон
        return self.prompt_template.format_messages(**body)

    def set_output(self, schema: Optional[type[BaseModel]] = None) -> None:
        if schema is not None:
            self.model = self.model.with_structured_output(schema=schema)

    def get_sync_response(self, body: dict = {}) -> Union[SchemaT, BaseMessage]:
        messages = self.get_prompt(body)
        result = self.model.invoke(messages)
        return self.__cast_llm_output(result=result)

    async def get_async_response(self, body: dict = {}) -> Union[SchemaT, BaseMessage]:
        messages = self.get_prompt(body)
        try:
            result = await self.model.ainvoke(messages)
        except OutputParserException as e:
            result = self.__fallback_from_error(e)
        return self.__cast_llm_output(result=result)

    async def get_stream_response(self, body: dict = {}) -> AsyncIterator[str]:
        messages = self.get_prompt(body)

        async for chunk in self.model.astream(messages):
            if chunk.content:
                yield chunk.content

    def __fallback_from_error(self, e: OutputParserException):
        raw_text = getattr(e, "llm_output", None) or str(e)
        if self._schema is not None and hasattr(self._schema, "model_fields"):
            # если схема — один текстовый филд (как CoverLetterResult.content),
            # просто кладём туда сырой текст
            field_names = list(self._schema.model_fields.keys())
            if len(field_names) == 1:
                return self._schema(**{field_names[0]: raw_text})
        raise e  # если схема сложнее одного поля — фолбэк не годится, пробрасываем дальше

    def __cast_llm_output(self, result: AIMessage) -> Union[SchemaT, BaseMessage]:
        if self._schema is not None:
            return cast(SchemaT, result)
        return result
