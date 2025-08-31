from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.user import User, SubscriptionStatus
from app.schemas.subscription import UserSubscriptionUpdate
from app.db.models.association_tables import user_tags
from app.db.models.tag import Tag
from uuid import UUID

class SubscriptionService:
    @staticmethod
    def get_user_subscription(db: Session, user_id: UUID):
        """Get user's subscription details"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user

    @staticmethod
    def update_subscription_status(
        db: Session, 
        user_id: UUID, 
        subscription_update: UserSubscriptionUpdate
    ):
        """Update user's subscription status"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update subscription status if provided
        if subscription_update.status:
            user.subscription_status = SubscriptionStatus(subscription_update.status)
        
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_tag_subscriptions(
        db: Session, 
        user_id: UUID, 
        tag_ids: List[UUID]
    ):
        """Update user's tag subscriptions"""
        # Get user with current tags
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get current tag IDs
        current_tag_ids = {tag.id for tag in user.tags}
        new_tag_ids = set(tag_ids)
        
        # Find tags to add and remove
        tags_to_add = new_tag_ids - current_tag_ids
        tags_to_remove = current_tag_ids - new_tag_ids
        
        # Get tag objects to add
        tags_to_add_objs = db.query(Tag).filter(Tag.id.in_(tags_to_add)).all()
        
        # Update user's tags
        user.tags.extend(tags_to_add_objs)
        
        # Remove tags not in the new list
        if tags_to_remove:
            # Remove association entries
            stmt = user_tags.delete().where(
                (user_tags.c.user_id == user_id) & 
                (user_tags.c.tag_id.in_(tags_to_remove))
            )
            db.execute(stmt)
        
        db.commit()
        
        # Refresh user to get updated tags
        db.refresh(user)
        
        return {
            "subscribed_tags": list(tags_to_add),
            "unsubscribed_tags": list(tags_to_remove)
        }

    @staticmethod
    def get_user_subscribed_tags(db: Session, user_id: UUID):
        """Get list of tags user is subscribed to"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user.tags
