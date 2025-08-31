# app/schemas/user.py

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import Field, EmailStr, field_validator
from app.schemas.base import BaseSchema
from app.db.models.user import SubscriptionStatus
from app.schemas.tag import TagRead

class UserBase(BaseSchema):
    email: EmailStr
    subscription_status: Optional[SubscriptionStatus] = Field(default=SubscriptionStatus.active)
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    is_email_verified: Optional[bool] = False
    is_premium: Optional[bool] = False

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    def password_strength_check(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class UserRead(BaseSchema):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    is_email_verified: Optional[bool] = None
    subscription_status: SubscriptionStatus
    tags: List[TagRead] = []
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    last_problem_sent_at: Optional[datetime] = None
    is_premium: bool = False
    

class UserUpdate(BaseSchema):
    full_name: Optional[str] = None

class UserLogin(BaseSchema):
    email: EmailStr
    password: str

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    email_verification_required: bool = False
    is_admin: bool = False
    email: Optional[str] = None
    full_name: Optional[str] = None

class TokenPayload(BaseSchema):
    sub: Optional[str] = None  # Changed from int to str to accept email addresses

class PasswordResetRequest(BaseSchema):
    """Schema for password reset request."""
    email: EmailStr

class PasswordReset(BaseSchema):
    """Schema for password reset with token."""
    token: str
    password: str
    
    @field_validator('password')
    def password_strength_check(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class PasswordChange(BaseSchema):
    """Schema for changing password while logged in."""
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    def password_strength_check(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
