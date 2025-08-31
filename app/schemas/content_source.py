# app/schemas/content_source.py

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas.base import BaseSchema
from app.db.models.content_source import SourcePlatform, ProcessingStatus
from app.schemas.problem import ProblemRead

class ContentSourceCreate(BaseSchema):
    source_platform: SourcePlatform
    source_identifier: str = Field(..., min_length=1)
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_tags: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]] = None
    processed_text: Optional[str] = None
    notes: Optional[str] = None
    processing_status: Optional[ProcessingStatus] = Field(default=ProcessingStatus.pending)

class ContentSourceRead(BaseSchema):
    id: UUID
    source_platform: SourcePlatform
    source_identifier: str
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_tags: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]]
    processed_text: Optional[str] = None
    notes: Optional[str]
    processing_status: ProcessingStatus
    ingested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    problems: List[ProblemRead] = []

class ContentSourceUpdate(BaseSchema):
    source_platform: Optional[SourcePlatform] = None
    source_identifier: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_tags: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]] = None
    processed_text: Optional[str] = None
    notes: Optional[str] = None
    processing_status: Optional[ProcessingStatus] = None
