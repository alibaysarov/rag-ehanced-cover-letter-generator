from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain import LetterPhraseType, TemplateCase, TemplateNodeKind, TemplateStatus


class PhraseWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: LetterPhraseType
    text: str = Field(min_length=1, max_length=2000)
    is_active: bool = True


class PhrasePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: LetterPhraseType | None = None
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    is_active: bool | None = None


class PhraseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: LetterPhraseType
    text: str
    is_active: bool
    used_in_templates: int
    created_at: datetime
    updated_at: datetime


class PhraseList(BaseModel):
    items: list[PhraseRead]
    page: int
    page_size: int
    total: int


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float


class TemplateNodeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    node_kind: TemplateNodeKind
    phrase_id: int | None = None
    position: Position


class TemplateEdgeWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    branch_order: int = Field(ge=0)


class TemplateWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = Field(min_length=1, max_length=120)
    template_case: TemplateCase = Field(alias="case")
    version: int | None = Field(default=None, ge=1)
    confirm_without_projects: bool = False
    root_node_id: UUID | None = None
    nodes: list[TemplateNodeWrite] = Field(max_length=100)
    edges: list[TemplateEdgeWrite] = Field(max_length=300)


class ActivateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)
    confirm_without_projects: bool = False


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vacancy_id: int


class TemplateNodeRead(TemplateNodeWrite):
    phrase: PhraseRead | None = None


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    name: str
    template_case: TemplateCase = Field(alias="case")
    status: TemplateStatus
    root_node_id: UUID | None
    version: int
    nodes: list[TemplateNodeRead]
    edges: list[TemplateEdgeWrite]
    created_at: datetime
    updated_at: datetime


class TemplateListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: int
    name: str
    template_case: TemplateCase = Field(alias="case")
    status: TemplateStatus
    root_node_id: UUID | None
    version: int
    has_projects_node: bool
    nodes_count: int
    edges_count: int
    created_at: datetime
    updated_at: datetime


class TemplateList(BaseModel):
    items: list[TemplateListItem]
    page: int
    page_size: int
    total: int


class PreviewResponse(BaseModel):
    detected_case: TemplateCase
    template_case: TemplateCase
    text: str
    node_path: list[UUID]
    warning: str | None = None
