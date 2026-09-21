from enum import Enum


class GenerationMode(str, Enum):
    """The immutable letter-generation strategy selected for a parsing job."""

    AI = "ai"
    TEMPLATE = "template"
