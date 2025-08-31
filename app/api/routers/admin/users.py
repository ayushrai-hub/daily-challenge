"""
Admin router for user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from uuid import UUID
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api import deps
from app.db.models.user import User, SubscriptionStatus
from app.schemas.user import UserRead
from app.schemas.admin_user import AdminUserUpdate, UserFilter
from app.repositories.admin_user import AdminUserRepository
from app.utils.logging_utils import log_admin_action

import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["admin-users"],
    dependencies=[Depends(deps.get_current_admin_user)],  # Only admins can access these routes
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin privileges required"},
        404: {"description": "User not found"}
    }
)


@router.get("", response_model=List[UserRead])
async def get_admin_users(
    response: Response,
    skip: int = 0,
    limit: int = 1000,  # Higher limit for admin view
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    # Search parameter
    search: Optional[str] = Query(None, description="Search in email and full name"),
    # Filter parameters
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    full_name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    is_email_verified: Optional[bool] = Query(None, description="Filter by email verification status"),
    subscription_status: Optional[SubscriptionStatus] = Query(None, description="Filter by subscription status"),
    db = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to retrieve all users with pagination, sorting, and filtering.
    
    Returns users ordered from newest to oldest (by creation date).
    """
    # Log admin action
    log_admin_action(
        user=current_user,
        action="view_admin_users",
        search_term=search,
        filters={
            "email": email,
            "is_active": is_active,
            "is_admin": is_admin,
            "subscription_status": subscription_status.value if subscription_status else None
        },
        page=page,
        page_size=page_size
    )
    
    # Use page and page_size for pagination
    if page and page_size:
        skip = (page - 1) * page_size
        limit = page_size
    
    # Initialize repo
    user_repo = AdminUserRepository(db)
    
    # Build filters from query parameters
    filters = {}
    if email:
        filters["email"] = email
    if full_name:
        filters["full_name"] = full_name
    if is_active is not None:
        filters["is_active"] = is_active
    if is_admin is not None:
        filters["is_admin"] = is_admin
    if is_email_verified is not None:
        filters["is_email_verified"] = is_email_verified
    if subscription_status:
        filters["subscription_status"] = subscription_status
    
    # Get users with filters and search
    users, total_count = user_repo.get_all_users(
        skip=skip,
        limit=limit,
        filters=filters,
        search=search
    )
    
    # Set total count header
    response.headers["X-Total-Count"] = str(total_count)
    
    return users


@router.get("/{user_id}", response_model=UserRead)
async def get_admin_user_detail(
    user_id: UUID,
    db = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to get detailed user information by ID.
    """
    # Log admin action
    log_admin_action(
        user=current_user,
        action="view_user_detail",
        user_id=str(user_id)
    )
    
    user_repo = AdminUserRepository(db)
    user = user_repo.get(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def update_admin_user(
    user_id: UUID,
    user_update: AdminUserUpdate,
    db = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to update user information.
    """
    # Get fields being updated for audit trail
    updated_fields = [k for k, v in user_update.model_dump(exclude_unset=True).items()]
    
    # Log admin action with context about what's being changed
    log_admin_action(
        user=current_user,
        action="update_admin_user",
        user_id=str(user_id),
        fields_updated=str(updated_fields),
        update_count=len(updated_fields)
    )
    
    # Prevent modifying own admin status
    if str(user_id) == str(current_user.id) and "is_admin" in updated_fields and not user_update.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges"
        )
    
    user_repo = AdminUserRepository(db)
    user = user_repo.admin_update_user(user_id, user_update)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    # Proper string formatting for logging
    logger.info(f"&&&&&&&&& User type: {type(user)}")
    logger.info(f"======= User object: {user}")
    # Add an INFO level log to ensure it appears even if DEBUG is disabled
    logger.info(f"Updated user {user_id} successfully")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_email_verified": user.is_email_verified,
        "subscription_status": user.subscription_status,
        "created_at": user.created_at,
        "updated_at": user.updated_at
    } # Return UserRead model for production


@router.post("/{user_id}/toggle-admin", response_model=UserRead)
async def toggle_admin_status(
    user_id: UUID,
    make_admin: bool,
    db = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to toggle admin status for a user.
    """
    # Prevent removing own admin status
    if str(user_id) == str(current_user.id) and not make_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin privileges"
        )
    
    # Log admin action
    log_admin_action(
        user=current_user,
        action="toggle_admin_status",
        user_id=str(user_id),
        make_admin=make_admin
    )
    
    user_repo = AdminUserRepository(db)
    user = user_repo.toggle_admin_status(user_id, make_admin)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/{user_id}/toggle-active", response_model=UserRead)
async def toggle_active_status(
    user_id: UUID,
    make_active: bool,
    db = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to toggle active status for a user.
    """
    # Prevent deactivating own account
    if str(user_id) == str(current_user.id) and not make_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Log admin action
    log_admin_action(
        user=current_user,
        action="toggle_active_status",
        user_id=str(user_id),
        make_active=make_active
    )
    
    user_repo = AdminUserRepository(db)
    user = user_repo.toggle_user_active_status(user_id, make_active)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
