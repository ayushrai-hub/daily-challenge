"""
Admin-specific user schemas.
"""
from typing import Optional
from pydantic import EmailStr

from app.schemas.base import BaseSchema
from app.db.models.user import SubscriptionStatus

class AdminUserUpdate(BaseSchema):
    """Schema for admin user updates with additional fields that only admins can modify."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_email_verified: Optional[bool] = None
    subscription_status: Optional[SubscriptionStatus] = None

class UserFilter(BaseSchema):
    """Schema for filtering users in admin endpoints."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_email_verified: Optional[bool] = None
    subscription_status: Optional[SubscriptionStatus] = None
