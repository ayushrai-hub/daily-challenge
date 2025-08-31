"""
Schemas for tag hierarchy relationships that enable multi-parent support for tags.
"""
from typing import List, Optional, Any
from pydantic import Field, ConfigDict
from uuid import UUID

from app.schemas.base import BaseSchema
from app.core.serialization import UUIDSTR


class TagHierarchyBase(BaseSchema):
    """Base schema for tag hierarchy relationship data."""
    parent_tag_id: UUIDSTR  # Using annotated UUID type for proper serialization
    child_tag_id: UUIDSTR   # Using annotated UUID type for proper serialization
    relationship_type: Optional[str] = "parent_child"  # Default relationship type


class TagHierarchyCreate(TagHierarchyBase):
    """Schema for creating a new tag hierarchy relationship."""
    pass


class TagHierarchyRead(TagHierarchyBase):
    """Schema for reading tag hierarchy data."""
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class TagRelationshipBulk(BaseSchema):
    """Schema for bulk operations on tag relationships."""
    tag_id: UUIDSTR
    parent_ids: List[UUIDSTR] = Field(default_factory=list)
    remove_parents: Optional[List[UUIDSTR]] = Field(default_factory=list)
    
    # Update to Pydantic V2 syntax
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tag_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "parent_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa7", "3fa85f64-5717-4562-b3fc-2c963f66afa8"],
                "remove_parents": ["3fa85f64-5717-4562-b3fc-2c963f66afa9"]
            }
        }
    )


class TagChildAssignment(BaseSchema):
    """Schema for assigning children to a parent tag."""
    parent_id: UUIDSTR  
    child_ids: List[UUIDSTR] = Field(default_factory=list)
    remove_children: Optional[List[UUIDSTR]] = Field(default_factory=list)
    
    # Update to Pydantic V2 syntax
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "child_ids": ["3fa85f64-5717-4562-b3fc-2c963f66afa7", "3fa85f64-5717-4562-b3fc-2c963f66afa8"],
                "remove_children": ["3fa85f64-5717-4562-b3fc-2c963f66afa9"]
            }
        }
    )
