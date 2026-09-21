from enum import Enum


class TemplateCase(str, Enum):
    NO_PORTFOLIO = "no_portfolio"
    RELEVANT_DOMAIN = "relevant_domain"
    PARTIAL_MATCH = "partial_match"
    NO_RELEVANT_PROJECTS = "no_relevant_projects"


class LetterPhraseType(str, Enum):
    OPENING = "opening"
    EXPERIENCE_BRIDGE = "experience_bridge"
    PORTFOLIO_INTRO = "portfolio_intro"
    STACK_SUMMARY = "stack_summary"
    CLOSING = "closing"
    CUSTOM = "custom"


class TemplateNodeKind(str, Enum):
    PHRASE = "phrase"
    PROJECTS = "projects"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
