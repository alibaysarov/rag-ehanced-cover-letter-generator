from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from fastapi import UploadFile




class LetterFromUrlRequest(BaseModel):
    """Request schema for creating letter from URL"""
    url: HttpUrl = Field(..., description="URL to extract content from")
    source_id: int = Field(..., description="Source ID of the CV in the database")
    file: Optional[UploadFile] = Field(None, description="Optional file to upload")

    class Config:
        arbitrary_types_allowed = True


class LetterFromTextRequest(BaseModel):
    """Request schema for creating letter from text"""
    name: str = Field(..., min_length=1, max_length=100, description="Job title")
    description: str = Field(..., min_length=1, max_length=500, description="Job description")
    source_id: int = Field(..., description="Source ID of the CV in the database")
    file: Optional[UploadFile] = Field(None, description="Optional file to upload")

    class Config:
        arbitrary_types_allowed = True


class CVUploadResponse(BaseModel):
    """Response schema for CV upload operations"""
    success: bool
    message: str
    data: Optional[dict] = None
    source_id: Optional[int] = None
    errors: Optional[list[str]] = None


class GeneralResponse(BaseModel):
    """Response schema for general operations"""
    success: bool
    data: Optional[dict] = None
    errors: Optional[list[str]] = None

class LetterResponse(GeneralResponse):
    """Response schema for letter operations"""
    message: str