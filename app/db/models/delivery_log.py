from sqlalchemy import Column, ForeignKey, DateTime, String, JSON, func, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum

from app.db.models.base_model import BaseModel

class DeliveryChannel(PyEnum):
    email = "email"        # Email delivery
    slack = "slack"        # Slack delivery (future)
    api = "api"            # Direct API delivery

class DeliveryStatus(PyEnum):
    scheduled = "scheduled"    # Delivery has been scheduled
    delivered = "delivered"    # Successfully delivered
    failed = "failed"          # Delivery attempt failed
    opened = "opened"          # User has opened/viewed the challenge
    completed = "completed"    # User has marked challenge as completed

class DeliveryLog(BaseModel):
    __tablename__ = "delivery_logs"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    status = Column(Enum(DeliveryStatus), default=DeliveryStatus.scheduled, nullable=False)
    delivery_channel = Column(Enum(DeliveryChannel), default=DeliveryChannel.email, nullable=False)
    meta = Column(JSON, nullable=True) 
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)  # When actually delivered
    opened_at = Column(DateTime(timezone=True), nullable=True)     # When user viewed the challenge
    completed_at = Column(DateTime(timezone=True), nullable=True)  # When user marked as complete

    # relationships
    user = relationship("User", back_populates="delivery_logs", lazy="selectin")
    problem = relationship("Problem", back_populates="delivery_logs", lazy="selectin")
