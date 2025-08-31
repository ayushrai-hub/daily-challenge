from sqlalchemy import Column, String, Enum, JSON, Text, ForeignKey, DateTime, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from enum import Enum as PyEnum
from app.db.models.base_model import BaseModel

class SourcePlatform(PyEnum):
    stackoverflow = "stackoverflow"
    gh_issues = "gh_issues"
    blog = "blog"
    reddit = "reddit"
    hackernews = "hackernews"  # Changed from hn="hackernews" to match database value
    dev_to = "dev_to"
    custom = "custom"

class ProcessingStatus(PyEnum):
    pending = "pending"       # Initial state, awaiting processing
    processed = "processed"   # Successfully processed
    failed = "failed"         # Processing failed

class ContentSource(BaseModel):
    __tablename__ = "content_sources"

    source_platform = Column(Enum(SourcePlatform), nullable=False)
    source_identifier = Column(String, nullable=False)
    source_url = Column(String, nullable=True)  # URL where content was sourced
    source_title = Column(String, nullable=True)  # Original title if available
    raw_data = Column(JSON, nullable=True)
    processed_text = Column(Text, nullable=True)  # Text that was input to LLM
    source_tags = Column(ARRAY(String), nullable=True)  # Tags from original source
    notes = Column(Text, nullable=True)
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.pending, nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)  # When processing completed

    # relationships
    problems = relationship("Problem", back_populates="content_source", lazy="selectin")
