"""
User profile management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api import deps
from app.schemas.user import UserRead, UserUpdate
from app.schemas.profile import ProfileUpdate
from app.repositories.user import UserRepository
from app.db.models.user import User

router = APIRouter(
    prefix="/profile",
    tags=["profile"],
    dependencies=[Depends(deps.get_current_active_user)],  # Apply authentication to all routes
)

@router.get("", response_model=UserRead)
async def read_current_user_profile(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Get current user's profile information.
    Requires email verification to access this endpoint.
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log user profile access
    log_user_activity(
        user=current_user,
        action="view_user_profile"
    )
    
    # Return the current user from the dependency
    return current_user


@router.put("", response_model=UserRead)
async def update_current_user_profile(
    profile_update: ProfileUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Update current user's profile information.
    Requires email verification to access this endpoint.
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log user profile update action
    log_user_activity(
        user=current_user,
        action="update_user_profile",
        updated_fields=str([k for k, v in profile_update.model_dump(exclude_unset=True).items()])
    )
    
    # Update only the fields that were provided
    user_repo = UserRepository(db)
    
    # Only update fields that were actually provided in the request
    update_data = profile_update.model_dump(exclude_unset=True)
    
    # Direct update using model attributes to avoid null constraints
    if "full_name" in update_data and update_data["full_name"] is not None:
        current_user.full_name = update_data["full_name"]
    
    # Save changes directly to the database
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    updated_user = current_user
    
    # Return the updated user
    return updated_user
