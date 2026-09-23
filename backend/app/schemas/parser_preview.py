from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.parser import FetchMode, ParserWrite


class PreviewRequest(BaseModel):
    parser: ParserWrite
    stage: Literal["list", "detail", "pagination"]
    search_text: str = Field(default="", max_length=500)
    page: int = Field(default=0, ge=0, le=50)
    url: str | None = Field(default=None, max_length=4096)

    @model_validator(mode="after")
    def validate_stage_payload(self):
        if self.stage == "detail" and not self.url:
            raise ValueError("url is required for detail preview")
        if self.stage != "detail" and self.url is not None:
            raise ValueError("url is only valid for detail preview")
        return self


class PreviewResponse(BaseModel):
    resolved_url: str
    fetch_mode: FetchMode
    stage: Literal["list", "detail", "pagination"]
    result: list[dict] | dict | int
    warnings: list[str] = Field(default_factory=list)
    timing_ms: int
