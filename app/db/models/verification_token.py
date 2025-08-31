"""
Verification token model for email verification.
"""
from datetime import datetime, timedelta, timezone
import secrets
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.models.base_model import BaseModel
from app.core.config import settings


class VerificationToken(BaseModel):
    """Model for storing email verification tokens."""
    __tablename__ = "verification_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    token_type = Column(String, nullable=False, default="email_verification")
    
    # Relationships
    user = relationship("User", backref="verification_tokens")
    
    @classmethod
    def create_token(cls, db, user_id, token_type="email_verification", expiration_hours=24):
        """
        Create a new verification token for a user.
        
        Args:
            db: Database session
            user_id: User ID to associate with the token
            token_type: Type of token (default: email_verification)
            expiration_hours: Token validity in hours (default: 24)
            
        Returns:
            The created token object
        """
        # Generate a secure token
        token_value = secrets.token_urlsafe(32)
        
        # Calculate expiration time with timezone awareness
        expiration_time = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)
        
        # Create the token
        token = cls(
            user_id=user_id,
            token=token_value,
            token_type=token_type,
            expires_at=expiration_time
        )
        
        db.add(token)
        db.commit()
        db.refresh(token)
        
        return token
    
    @classmethod
    def validate_token(cls, db, token_value, token_type="email_verification"):
        """
        Validate a token and return the associated user ID if valid.
        
        Args:
            db: Database session
            token_value: Token string to validate
            token_type: Type of token to validate
            
        Returns:
            User ID if valid, None otherwise
        """
        # Use timezone-aware datetime for comparison with timezone-aware fields
        now = datetime.now(timezone.utc)
        
        # Find the token
        token = db.query(cls).filter(
            cls.token == token_value,
            cls.token_type == token_type,
            cls.is_used == False,
            cls.expires_at > now
        ).first()
        
        if not token:
            return None
            
        return token.user_id
    
    @classmethod
    def mark_as_used(cls, db, token_value):
        """
        Mark a token as used.
        
        Args:
            db: Database session
            token_value: Token string to mark as used
            
        Returns:
            Token object if successful, None otherwise
        """
        token = db.query(cls).filter(cls.token == token_value).first()
        
        if not token:
            return None
            
        token.is_used = True
        db.commit()
        db.refresh(token)
        
        return token
        
    @classmethod
    def check_recent_token(cls, db, user_id, minutes=5, token_type="email_verification"):
        """
        Check if a user has had a token generated within the cooldown period.
        
        Args:
            db: Database session
            user_id: User ID to check
            minutes: Cooldown period in minutes
            token_type: Type of token to check
            
        Returns:
            Token object if one exists within cooldown period, None otherwise
        """
        # Calculate cooldown threshold time with timezone awareness
        cooldown_threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        # Check for tokens created after the threshold
        recent_token = db.query(cls).filter(
            cls.user_id == user_id,
            cls.token_type == token_type,
            cls.created_at > cooldown_threshold
        ).order_by(cls.created_at.desc()).first()
        
        return recent_token
