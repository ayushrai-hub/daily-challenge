# app/schemas/problem.py


from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import Field, field_validator, computed_field
from app.schemas.base import BaseSchema
from app.db.models.problem import VettingTier, DifficultyLevel, ProblemStatus
from app.schemas.tag import TagRead
from app.utils.markdown_utils import markdown_to_html

class ProblemCreate(BaseSchema):
    title: str = Field(..., min_length=1)
    description: str
    solution: Optional[str] = None
    vetting_tier: Optional[VettingTier] = Field(default=VettingTier.tier3_needs_review)
    status: Optional[ProblemStatus] = Field(default=ProblemStatus.draft)
    difficulty_level: DifficultyLevel = Field(default=DifficultyLevel.medium)
    content_source_id: Optional[UUID] = Field(default=None)
    problem_metadata: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('content_source_id')
    def validate_content_source_id(cls, v):
        if v == None:  # Treat None as None
            return None
        return v

class ProblemRead(BaseSchema):
    id: UUID
    title: str
    description: str
    solution: Optional[str]
    vetting_tier: VettingTier
    status: ProblemStatus
    difficulty_level: DifficultyLevel
    content_source_id: Optional[UUID]
    approved_at: Optional[datetime] = None
    tags: List[TagRead] = []
    problem_metadata: Optional[Dict[str, Any]] = None
    
    @computed_field
    @property
    def rendered_description(self) -> str:
        """Return the description rendered as HTML from Markdown."""
        return markdown_to_html(self.description) if self.description else ""
    
    @computed_field
    @property
    def rendered_solution(self) -> Optional[str]:
        """Return the solution rendered as HTML from Markdown if available."""
        return markdown_to_html(self.solution) if self.solution else None

class ProblemUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    solution: Optional[str] = None
    vetting_tier: Optional[VettingTier] = None
    status: Optional[ProblemStatus] = None
    difficulty: Optional[DifficultyLevel] = None
    content_source_id: Optional[UUID] = None


class ProblemReadDetailed(ProblemRead):
    """Extended problem schema with additional Markdown preview features."""
    
    @computed_field
    @property
    def description_preview(self) -> Dict[str, Any]:
        """Return a complete preview of the description with HTML, TOC, and CSS."""
        from app.utils.markdown_utils import markdown_preview
        return markdown_preview(self.description) if self.description else {}
    
    @computed_field
    @property
    def solution_preview(self) -> Optional[Dict[str, Any]]:
        """Return a complete preview of the solution with HTML, TOC, and CSS if available."""
        if not self.solution:
            return None
        
        from app.utils.markdown_utils import markdown_preview
        return markdown_preview(self.solution)
