from sqlalchemy import Column, String, Enum, func, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.base_model import BaseModel
from app.db.models.association_tables import user_tags

from enum import Enum as PyEnum

class SubscriptionStatus(PyEnum):
    active = "active"
    paused = "paused"
    unsubscribed = "unsubscribed"

class User(BaseModel):
    __tablename__ = "users"

    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False, server_default='false')
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.active)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Daily challenge tracking fields
    last_problem_sent_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=True)
    last_problem_sent_at = Column(DateTime(timezone=True), nullable=True)
    is_premium = Column(Boolean, default=False, nullable=False, server_default='false')

    # relationships
    # Use the imported user_tags table directly
    tags = relationship("Tag", secondary=user_tags, back_populates="users", lazy="selectin")
    delivery_logs = relationship("DeliveryLog", back_populates="user", lazy="selectin")
    # Use string-based relationship pattern to avoid circular dependencies
    emails = relationship("EmailQueue", back_populates="user", lazy="selectin")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_email_verified": self.is_email_verified,
            "subscription_status": self.subscription_status.value if self.subscription_status else None,
            "last_login": self.last_login,
            "last_problem_sent_at": self.last_problem_sent_at,
            "is_premium": self.is_premium,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "created_at": tag.created_at,
                    "updated_at": tag.updated_at,
                }
                for tag in self.tags
            ],
        }
