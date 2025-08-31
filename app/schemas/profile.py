"""
User profile schemas.
"""
from typing import Optional
from pydantic import validator
from app.schemas.base import BaseSchema

class ProfileUpdate(BaseSchema):
    """Schema for updating user profile information."""
    full_name: Optional[str] = None
    
    @validator('full_name')
    def validate_full_name(cls, v):
        """Validate that full name is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Full name cannot be empty")
        return v
    
