"""
Schemas for tag normalization entities that handle the review and approval process for AI-generated tags.
"""
from typing import List, Optional, Any, Dict
from pydantic import Field, ConfigDict, model_validator
from uuid import UUID
from datetime import datetime

from app.schemas.base import BaseSchema
from app.db.models.tag_normalization import TagReviewStatus, TagSource
from app.core.serialization import UUIDSTR

class TagNormalizationBase(BaseSchema):
    """Base schema for tag normalization data with common fields."""
    original_name: str = Field(..., min_length=1, max_length=100)
    normalized_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    parent_tag_ids: Optional[List[UUIDSTR]] = None
    review_status: TagReviewStatus = TagReviewStatus.pending
    admin_notes: Optional[str] = None
    source: TagSource = TagSource.ai_generated
    confidence_score: Optional[float] = None
    auto_approved: bool = False


class TagNormalizationCreate(TagNormalizationBase):
    """Schema for creating a new tag normalization entry."""
    approved_tag_id: Optional[UUIDSTR] = None
    reviewed_by: Optional[UUIDSTR] = None
    reviewed_at: Optional[datetime] = None


class TagNormalizationUpdate(BaseSchema):
    """Schema for updating an existing tag normalization entry."""
    original_name: Optional[str] = Field(None, min_length=1, max_length=100)
    normalized_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_tag_ids: Optional[List[UUIDSTR]] = None
    review_status: Optional[TagReviewStatus] = None
    admin_notes: Optional[str] = None
    source: Optional[TagSource] = None
    confidence_score: Optional[float] = None
    reviewed_by: Optional[UUIDSTR] = None
    reviewed_at: Optional[datetime] = None
    approved_tag_id: Optional[UUIDSTR] = None
    auto_approved: Optional[bool] = None


class TagNormalizationRead(TagNormalizationBase):
    """Schema for read operations with additional fields from the database."""
    id: UUIDSTR
    created_at: datetime
    updated_at: datetime
    approved_tag_id: Optional[UUIDSTR] = None
    
    # Additional field for API responses to include approved tag data
    approved_tag: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    
    @model_validator(mode='before')
    @classmethod
    def preprocess_model(cls, data: Any) -> Any:
        """Handle conversion from SQLAlchemy models."""
        # Handle directly passed SQLAlchemy model
        if hasattr(data, '__table__'):
            # Extract approved tag if relationship is loaded
            approved_tag = None
            if hasattr(data, 'approved_tag') and data.approved_tag is not None:
                approved_tag = {
                    'id': data.approved_tag.id,
                    'name': data.approved_tag.name,
                    'description': getattr(data.approved_tag, 'description', None)
                }
            
            # Build data dictionary with proper field values
            return {
                'id': data.id,
                'original_name': data.original_name,
                'normalized_name': data.normalized_name,
                'description': data.description,
                'parent_tag_ids': data.parent_tag_ids,
                'review_status': data.review_status,
                'admin_notes': data.admin_notes,
                'source': data.source,
                'confidence_score': data.confidence_score,
                'reviewed_by': data.reviewed_by,
                'reviewed_at': data.reviewed_at,
                'approved_tag_id': data.approved_tag_id,
                'auto_approved': data.auto_approved,
                'created_at': data.created_at,
                'updated_at': data.updated_at,
                'approved_tag': approved_tag
            }
        
        return data


class TagNormalizationReview(BaseSchema):
    """Schema for reviewing and approving/rejecting tag normalization entries."""
    review_status: TagReviewStatus
    admin_notes: Optional[str] = None
    reviewed_by: Optional[UUIDSTR] = None
    
    # When approving, these fields can be provided to create/update the approved tag
    approved_name: Optional[str] = None  # If different from normalized_name
    approved_description: Optional[str] = None
    approved_tag_type: Optional[str] = None
    approved_parent_ids: Optional[List[UUIDSTR]] = None  # Parent tag IDs for multi-parent support


class TagNormalizationBulkReview(BaseSchema):
    """Schema for bulk reviewing multiple tag normalization entries."""
    tag_normalization_ids: List[UUIDSTR]
    review_data: TagNormalizationReview


class TagNormalizationApprove(BaseSchema):
    """Schema for approving a tag normalization and creating/linking to a tag."""
    # ID of the normalization to approve - required for bulk approval
    normalization_id: Optional[UUIDSTR] = None
    
    # If provided, map to an existing tag instead of creating a new one
    existing_tag_id: Optional[UUIDSTR] = None
    
    # These fields are used when creating a new tag
    tag_name: Optional[str] = None  # If None, normalized_name will be used
    description: Optional[str] = None
    tag_type: Optional[str] = None
    parent_tag_ids: Optional[List[UUIDSTR]] = None
    
    # Admin notes for the approval
    admin_notes: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_approval_data(self):
        """Validate that either an existing tag or name for a new tag is provided."""
        # For the single tag approval endpoint, normalization_id is not required
        # For bulk approvals, if no normalization_id is provided, skip validation
        if not self.existing_tag_id and not self.tag_name:
            if not self.normalization_id:  # Skip validation if not in a bulk operation
                return self
            raise ValueError("Either existing_tag_id or tag_name must be provided")
        return self


class TagNormalizationsList(BaseSchema):
    """Schema for paginated list of tag normalizations."""
    items: List[TagNormalizationRead]
    total: int
    page: int
    page_size: int
    pages: int
