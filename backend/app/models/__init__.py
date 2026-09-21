# Models package
from .auto_parsed_job import AutoParsedJob
from .base import Base, BaseModel
from .cover_letter_template import (
    CoverLetterTemplate,
    CoverLetterTemplateEdge,
    CoverLetterTemplateNode,
    LetterPhrase,
    LetterPhraseType,
    TemplateCase,
    TemplateNodeKind,
    TemplateStatus,
)
from .cv import CV
from .cv_chunk import CVChunk
from .letter import Letter
from .parser import Parser, ParserUsage
from .parsing_job import ParsingJob
from .parsing_site_job import ParsingSiteJob
from .project import Project
from .sent_cover_letter import SentCoverLetter
from .user import User

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "CV",
    "CVChunk",
    "Letter",
    "SentCoverLetter",
    "ParsingJob",
    "ParsingSiteJob",
    "Parser",
    "ParserUsage",
    "AutoParsedJob",
    "Project",
    "LetterPhrase",
    "CoverLetterTemplate",
    "CoverLetterTemplateNode",
    "CoverLetterTemplateEdge",
    "TemplateCase",
    "LetterPhraseType",
    "TemplateNodeKind",
    "TemplateStatus",
]
