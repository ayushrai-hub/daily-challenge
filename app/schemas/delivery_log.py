# app/schemas/delivery_log.py

from datetime import datetime
from typing import Optional, Dict, Any, Annotated
# Update to Pydantic V2 compatible imports
from pydantic import Field, field_validator
from uuid import UUID
import uuid as uuid_pkg
from app.schemas.base import BaseSchema
from app.db.models.delivery_log import DeliveryStatus, DeliveryChannel

class DeliveryLogCreate(BaseSchema):
    user_id: UUID
    problem_id: UUID
    status: Optional[DeliveryStatus] = Field(default=DeliveryStatus.scheduled)
    delivery_channel: Optional[DeliveryChannel] = Field(default=DeliveryChannel.email)
    meta: Optional[Dict[str, Any]] = None
    
    # Update to use field_validator from Pydantic V2
    @field_validator('user_id', 'problem_id', mode='before')
    @classmethod  # field_validator requires the classmethod decorator
    def validate_uuid(cls, v):
        """Ensure UUID fields are proper UUID objects, converting from strings if needed."""
        if isinstance(v, str):
            try:
                return uuid_pkg.UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        return v

class DeliveryLogRead(BaseSchema):
    id: UUID
    user_id: UUID
    problem_id: UUID
    status: DeliveryStatus
    delivery_channel: DeliveryChannel
    scheduled_at: datetime
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None

class DeliveryLogUpdate(BaseSchema):
    user_id: Optional[UUID] = None
    problem_id: Optional[UUID] = None
    status: Optional[DeliveryStatus] = None
    delivery_channel: Optional[DeliveryChannel] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    meta: Optional[Dict[str, Any]] = None
