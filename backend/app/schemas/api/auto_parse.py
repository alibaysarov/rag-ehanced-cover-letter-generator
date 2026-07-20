from pydantic import BaseModel


class AutoParseResponse(BaseModel):
    total: int
    generated: int


class StartParseRequest(BaseModel):
    query: str


class MarkAppliedRequest(BaseModel):
    letter_text: str = ""
