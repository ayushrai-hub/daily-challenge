from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List
import logging

from app.api import deps
from app.schemas.subscription import (
    UserSubscriptionRead,
    UserSubscriptionUpdate,
    UserTagSubscription,
    UserTagSubscriptionResponse,
    SubscriptionStatusResponse
)
from app.services.subscription_service import SubscriptionService
from app.schemas.tag import TagRead
from app.db.models.user import User

router = APIRouter(
    prefix="/subscriptions",
    tags=["subscriptions"],
    # Changed from get_current_active_user to get_current_verified_user
    # This ensures all routes in this router require email verification
    dependencies=[Depends(deps.get_current_verified_user)]
)

@router.get("/me", response_model=UserSubscriptionRead)
async def get_subscription(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Get current user's subscription details
    """
    user = SubscriptionService.get_user_subscription(db, current_user.id)
    return {
        "status": user.subscription_status.value,
        "user_id": user.id
    }

@router.put("/me", response_model=UserSubscriptionRead)
async def update_subscription(
    subscription_in: UserSubscriptionUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Update current user's subscription status
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log subscription update with before/after status
    log_user_activity(
        user=current_user,
        action="update_subscription_status",
        previous_status=current_user.subscription_status.value if hasattr(current_user, 'subscription_status') else None,
        new_status=subscription_in.status
    )
    
    user = SubscriptionService.update_subscription_status(
        db=db,
        user_id=current_user.id,
        subscription_update=subscription_in
    )
    return {
        "status": user.subscription_status.value,
        "user_id": user.id
    }

@router.get("/me/tags", response_model=List[TagRead])
async def get_subscribed_tags(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Get list of tags user is subscribed to
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log user viewing their tag subscriptions
    log_user_activity(
        user=current_user,
        action="view_subscribed_tags"
    )
    
    try:
        # Get user's tags from the database
        user_tags = SubscriptionService.get_user_subscribed_tags(db, current_user.id)
        
        # Sanitize the tags to ensure they have valid children arrays
        if user_tags:
            for tag in user_tags:
                if not hasattr(tag, 'children') or tag.children is None:
                    tag.children = []
                # Log for debugging
                logging.debug(f"Tag {tag.id} has children: {tag.children}")
                
        return user_tags
    except Exception as e:
        # Log the exception
        logging.error(f"Error processing subscribed tags: {str(e)}")
        
        # Get user's tags manually and create simplified tag objects
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or not user.tags:
            return []
            
        # Create simplified tag objects that avoid the validation error
        simplified_tags = []
        for tag in user.tags:
            try:
                simplified_tags.append({
                    "id": tag.id,
                    "name": tag.name,
                    "description": tag.description,
                    "tag_type": tag.tag_type,
                    "is_featured": tag.is_featured,
                    "is_private": tag.is_private,
                    "parent_tag_id": tag.parent_tag_id,
                    "created_at": tag.created_at,
                    "updated_at": tag.updated_at,
                    "children": []  # Empty children list to avoid validation issues
                })
            except Exception as tag_err:
                logging.error(f"Error processing tag {tag.id}: {str(tag_err)}")
                # Continue with next tag
                continue
                
        return simplified_tags

@router.put("/me/tags", response_model=UserTagSubscriptionResponse)
async def update_tag_subscriptions(
    tag_subscription: UserTagSubscription,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Update user's tag subscriptions
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log the tag subscription update with the list of tag IDs
    log_user_activity(
        user=current_user,
        action="update_tag_subscriptions",
        tag_count=len(tag_subscription.tag_ids),
        tag_ids=str([str(tag_id) for tag_id in tag_subscription.tag_ids]) if tag_subscription.tag_ids else "[]"
    )
    
    try:
        result = SubscriptionService.update_tag_subscriptions(
            db=db,
            user_id=current_user.id,
            tag_ids=tag_subscription.tag_ids
        )
        
        # Log the result of the update operation
        logging.info(
            f"User {current_user.id} updated tag subscriptions: {len(result['subscribed_tags'])} subscribed, {len(result['unsubscribed_tags'])} unsubscribed"
        )
        
        return UserTagSubscriptionResponse(
            subscribed_tags=result["subscribed_tags"],
            unsubscribed_tags=result["unsubscribed_tags"]
        )
    except Exception as e:
        logging.error(f"Error updating tag subscriptions for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tag subscriptions: {str(e)}"
        )

@router.post("/me/pause", response_model=SubscriptionStatusResponse)
async def pause_subscription(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Pause the current user's subscription
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log subscription pause with previous status
    log_user_activity(
        user=current_user,
        action="pause_subscription",
        previous_status=current_user.subscription_status.value if hasattr(current_user, 'subscription_status') else None
    )
    
    user = SubscriptionService.update_subscription_status(
        db=db,
        user_id=current_user.id,
        subscription_update=UserSubscriptionUpdate(status="paused")
    )
    return {
        "status": user.subscription_status.value,
        "message": "Subscription has been paused. You will not receive any emails until you resume."
    }

@router.post("/me/resume", response_model=SubscriptionStatusResponse)
async def resume_subscription(
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db)
):
    """
    Resume the current user's subscription
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log subscription resume with previous status
    log_user_activity(
        user=current_user,
        action="resume_subscription",
        previous_status=current_user.subscription_status.value if hasattr(current_user, 'subscription_status') else None
    )
    
    user = SubscriptionService.update_subscription_status(
        db=db,
        user_id=current_user.id,
        subscription_update=UserSubscriptionUpdate(status="active")
    )
    return {
        "status": user.subscription_status.value,
        "message": "Subscription has been resumed. You will start receiving emails again."
    }
