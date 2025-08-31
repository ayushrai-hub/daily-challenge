# app/repositories/user.py

from typing import List, Optional, Any, Dict

from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import select, func

from app.db.models.user import User
from app.db.models.tag import Tag
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository for User model providing CRUD operations and user-specific queries."""
    
    def __init__(self, db: Session):
        super().__init__(model=User, db=db)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User instance or None if not found
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_subscription_status(self, status: str, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get users by subscription status.
        
        Args:
            status: Subscription status to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of User instances
        """
        return self.db.query(User).filter(
            User.subscription_status == status
        ).offset(skip).limit(limit).all()
    
    def get_users_with_tags(self, tag_ids: List[UUID], skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get users who have specific tags.
        
        Args:
            tag_ids: List of tag IDs to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of User instances
        """
        # Use the relationship between users and tags through user_tags
        result = self.db.query(User).filter(
            User.tags.any(Tag.id.in_(tag_ids))
        ).offset(skip).limit(limit).all()
        
        return result
    
    def update_subscription_status(self, user_id: UUID, new_status: str) -> Optional[User]:
        """
        Update a user's subscription status.
        
        Args:
            user_id: ID of the user to update
            new_status: New subscription status
            
        Returns:
            Updated User instance or None if not found
        """
        user = self.get(user_id)
        if not user:
            return None
        
        user.subscription_status = new_status
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
