# app/schemas/tag.py

from typing import List, Optional, Union, Any, Set
from pydantic import Field, ConfigDict, model_validator, field_validator
from uuid import UUID
from datetime import datetime
from app.schemas.base import BaseSchema
from app.db.models.tag import TagType
from app.core.serialization import UUIDSTR


class TagBase(BaseSchema):
    """Base schema for tag data with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tag_type: Optional[TagType] = Field(default=TagType.concept)
    is_featured: bool = False
    is_private: bool = False
    parent_ids: List[UUIDSTR] = Field(default_factory=list)
    
    @field_validator('name')
    def name_must_not_be_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty')
        return v


class TagCreate(TagBase):
    """Schema for creating a new tag."""
    # For backward compatibility with existing code
    parent_tag_id: Optional[UUIDSTR] = None
    
    @model_validator(mode='after')
    def process_parent_fields(self) -> 'TagCreate':
        """Ensure parent_tag_id is added to parent_ids for backward compatibility"""
        # If parent_tag_id is set but not in parent_ids, add it to parent_ids
        if self.parent_tag_id and (not self.parent_ids or self.parent_tag_id not in self.parent_ids):
            self.parent_ids.append(self.parent_tag_id)
        return self


class TagUpdate(BaseSchema):
    """Schema for updating an existing tag."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    tag_type: Optional[TagType] = None
    is_featured: Optional[bool] = None
    is_private: Optional[bool] = None
    parent_ids: Optional[List[UUIDSTR]] = None
    # For backward compatibility
    parent_tag_id: Optional[UUIDSTR] = None
    
    @model_validator(mode='after')
    def process_parent_fields(self) -> 'TagUpdate':
        """Ensure parent_tag_id is added to parent_ids for backward compatibility"""
        # If parent_tag_id is set and parent_ids is provided, make sure parent_tag_id is included
        if self.parent_tag_id is not None and self.parent_ids is not None:
            if self.parent_tag_id not in self.parent_ids:
                self.parent_ids.append(self.parent_tag_id)
        # If only parent_tag_id is set, initialize parent_ids with it
        elif self.parent_tag_id is not None and self.parent_ids is None:
            self.parent_ids = [self.parent_tag_id]
        return self


class TagRead(TagBase):
    """Schema for read operations with additional fields from the database."""
    id: UUIDSTR
    created_at: datetime
    updated_at: datetime
    # List of child tags by their UUIDs
    children: List[UUIDSTR] = Field(default_factory=list)
    # For backward compatibility
    parent_tag_id: Optional[UUIDSTR] = None
    # New fields for multi-parent support
    parent_tag_ids: List[UUIDSTR] = Field(default_factory=list)
    child_ids: List[UUIDSTR] = Field(default_factory=list)
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    
    @model_validator(mode='before')
    @classmethod
    def preprocess_model(cls, data: Any) -> Any:
        """Handle conversion from SQLAlchemy models and ensure children/parents fields are valid."""
        # Handle directly passed SQLAlchemy model
        if hasattr(data, '__table__'):
            # Extract children IDs if relationship is loaded
            children = []
            child_ids = []
            if hasattr(data, 'children'):
                try:
                    # Try to iterate - this will work if it's a list or SQLAlchemy collection
                    children = [child.id for child in data.children if hasattr(child, 'id')]
                    child_ids = children.copy()  # Same values, just for clarity
                except TypeError:
                    # If not iterable, check if it's a single object with id
                    if hasattr(data.children, 'id'):
                        children = [data.children.id]
                        child_ids = children.copy()
            
            # Extract parent IDs if relationship is loaded
            parent_ids = []
            if hasattr(data, 'parents'):
                try:
                    # Try to iterate - this will work if it's a list or SQLAlchemy collection
                    parent_ids = [parent.id for parent in data.parents if hasattr(parent, 'id')]
                except TypeError:
                    # If not iterable, check if it's a single object with id
                    if hasattr(data.parents, 'id'):
                        parent_ids = [data.parents.id]
            
            # For backward compatibility, set parent_tag_id to the first parent if there is one
            parent_tag_id = parent_ids[0] if parent_ids else None
                
            # Build data dictionary with proper field values
            return {
                'id': data.id,
                'name': data.name,
                'description': getattr(data, 'description', None),
                'tag_type': getattr(data, 'tag_type', None),
                'is_featured': getattr(data, 'is_featured', False),
                'is_private': getattr(data, 'is_private', False),
                'parent_ids': parent_ids,
                'parent_tag_ids': parent_ids,  # Same as parent_ids but named to match API expectations
                'parent_tag_id': parent_tag_id,  # For backward compatibility
                'created_at': getattr(data, 'created_at', None),
                'updated_at': getattr(data, 'updated_at', None),
                'children': children,
                'child_ids': child_ids
            }
        
        # Process dictionary input
        if isinstance(data, dict):
            # Ensure all list fields have proper defaults
            for field in ['children', 'child_ids', 'parent_ids', 'parent_tag_ids']:
                if field not in data or data[field] is None:
                    data[field] = []
                elif not isinstance(data[field], list):
                    data[field] = [data[field]] if data[field] else []
            
            # Backward compatibility: convert parent_tag_id to parent_ids if needed
            if 'parent_tag_id' in data and data['parent_tag_id'] and 'parent_ids' not in data:
                data['parent_ids'] = [data['parent_tag_id']]
                data['parent_tag_ids'] = [data['parent_tag_id']]
                
            # For new field structure compatibility, set parent_tag_id to first parent_id if it exists
            if 'parent_tag_id' not in data or data['parent_tag_id'] is None:
                if 'parent_ids' in data and data['parent_ids'] and len(data['parent_ids']) > 0:
                    data['parent_tag_id'] = data['parent_ids'][0]
                elif 'parent_tag_ids' in data and data['parent_tag_ids'] and len(data['parent_tag_ids']) > 0:
                    data['parent_tag_id'] = data['parent_tag_ids'][0]
                else:
                    data['parent_tag_id'] = None
        
        return data
