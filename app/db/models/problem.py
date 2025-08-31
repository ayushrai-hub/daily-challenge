from sqlalchemy import Column, String, Text, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict

from app.db.models.base_model import BaseModel
from app.db.models.association_tables import problem_tags
from app.db.models.json_type import JSONType
from enum import Enum as PyEnum

class VettingTier(PyEnum):
    tier1_manual = "tier1_manual"  # Manually vetted, highest quality
    tier2_ai = "tier2_ai"          # AI reviewed, needs light human check
    tier3_needs_review = "tier3_needs_review"  # Raw generated content needing full review

class DifficultyLevel(PyEnum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class ProblemStatus(PyEnum):
    draft = "draft"          # Initial state
    approved = "approved"    # Reviewed and ready for delivery
    archived = "archived"    # No longer in active rotation
    pending = "pending"      # Added to match the fixed schema enum value

class Problem(BaseModel):
    __tablename__ = "problems"

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    solution = Column(Text, nullable=True)
    vetting_tier = Column(Enum(VettingTier), default=VettingTier.tier3_needs_review, nullable=False)
    status = Column(Enum(ProblemStatus), default=ProblemStatus.draft, nullable=False)
    difficulty_level = Column(Enum(DifficultyLevel), nullable=False)
    content_source_id = Column(UUID(as_uuid=True), ForeignKey("content_sources.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata stored as JSON for flexibility
    # Uses JSONB for PostgreSQL and serialized JSON for SQLite
    # Used to store additional information like pending tags and other AI-generated attributes
    problem_metadata = Column(MutableDict.as_mutable(JSONType), nullable=True, default={})
    
    # Use imported problem_tags table directly
    tags = relationship("Tag", secondary=problem_tags, back_populates="problems", lazy="selectin")
    delivery_logs = relationship("DeliveryLog", back_populates="problem", lazy="selectin")
    content_source = relationship("ContentSource", back_populates="problems", lazy="selectin")
