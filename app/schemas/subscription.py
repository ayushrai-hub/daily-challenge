from enum import Enum
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Enums
class SubscriptionStatus(str, Enum):
    active = "active"
    paused = "paused"
    unsubscribed = "unsubscribed"

# Request/Response Models
class UserSubscriptionBase(BaseModel):
    status: Optional[SubscriptionStatus] = Field(None, description="Current subscription status")

class UserSubscriptionUpdate(UserSubscriptionBase):
    pass

class UserSubscriptionRead(UserSubscriptionBase):
    status: SubscriptionStatus
    user_id: UUID
    
    # Update to Pydantic V2 syntax
    model_config = ConfigDict(from_attributes=True)  # Replaces orm_mode=True

# Tag Subscription Models
class UserTagSubscription(BaseModel):
    tag_ids: List[UUID] = Field(..., description="List of tag IDs to subscribe to")

class UserTagSubscriptionResponse(BaseModel):
    subscribed_tags: List[UUID] = Field(..., description="List of subscribed tag IDs")
    unsubscribed_tags: List[UUID] = Field(..., description="List of unsubscribed tag IDs")

# Response Models
class SubscriptionStatusResponse(BaseModel):
    status: SubscriptionStatus
    message: str
