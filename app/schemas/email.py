from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from app.schemas.base import BaseSchema

class EmailBase(BaseSchema):
    user_id: Optional[UUID] = None
    email_type: str  # e.g., welcome, daily_challenge, etc.
    recipient: EmailStr
    subject: str
    html_content: str
    text_content: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    problem_id: Optional[UUID] = None  # For daily challenge emails

class EmailCreate(EmailBase):
    pass

class EmailRead(EmailBase):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class EmailVerificationRequest(BaseSchema):
    """Schema for email verification request."""
    token: str = Field(..., description="Verification token sent to user's email")
