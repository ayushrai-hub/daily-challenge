from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from uuid import uuid4
import enum

from app.db.models.base_model import BaseModel

class EmailStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"

class EmailQueue(BaseModel):
    __tablename__ = "email_queue"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    email_type = Column(String, index=True, nullable=False)  # welcome, daily_challenge, subscription_update, etc.
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)
    
    # Metadata for the email
    template_id = Column(String, nullable=True)
    template_data = Column(JSON, nullable=True)
    
    # Delivery status and tracking
    status = Column(Enum(EmailStatus), default=EmailStatus.pending, index=True)
    scheduled_for = Column(DateTime, default=datetime.utcnow, index=True)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    tracking_id = Column(String, default=lambda: str(uuid4()), index=True)
    
    # Retry and failure tracking
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retry attempts
    last_retry_at = Column(DateTime, nullable=True)          # When last retry was attempted
    max_retries = Column(Integer, default=3, nullable=False) # Maximum number of retries to attempt
    delivery_data = Column(JSON, nullable=True)              # Response from email API
    
    # Simple string-based relationship to avoid circular dependencies
    user = relationship("User", back_populates="emails")
    
    # For emails related to problems (like daily challenge emails)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=True)
    problem = relationship("Problem", backref="emails")
