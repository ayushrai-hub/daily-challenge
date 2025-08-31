from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.api import deps
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.schemas.profile import ProfileUpdate
from app.repositories.user import UserRepository
from app.db.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(deps.get_current_active_user)],  # Apply base authentication to all routes
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Email verification or admin required"}}
)

@router.post("", response_model=UserRead)
async def create_user(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can create users
):
    """
    Create a new user.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin user creation action
    log_admin_action(
        user=current_user,
        action="create_user",
        new_user_email=user_in.email,
        is_admin=bool(user_in.is_admin) if hasattr(user_in, 'is_admin') else False,
        subscription_status=str(user_in.subscription_status) if hasattr(user_in, 'subscription_status') else None
    )
    
    try:
        # Convert the subscription_status from string to enum if needed
        # Remove debug prints in production code
        # print(f"Creating user with data: {user_in}")
        # print(f"Subscription status type: {type(user_in.subscription_status)}")
        
        
        if hasattr(user_in, 'subscription_status') and isinstance(user_in.subscription_status, str):
            from app.db.models.user import SubscriptionStatus
            try:
                user_in.subscription_status = SubscriptionStatus(user_in.subscription_status)
                print(f"Converted subscription_status to enum: {user_in.subscription_status}")
            except ValueError as e:
                print(f"Invalid subscription status: {user_in.subscription_status}, error: {e}")
                # Default to active
                user_in.subscription_status = SubscriptionStatus.active
                
        user_repo = UserRepository(db)
        user = user_repo.create(user_in)
        return user
    except Exception as e:
        import traceback
        print(f"Error creating user: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Return more details about the error
        print(f"User data: {user_in}")
        
        # Re-raise so FastAPI can handle it
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.get("", response_model=List[UserRead])
async def read_users(
    skip: int = 0,
    limit: int = 1000,
    # Filter parameters
    email: Optional[str] = None,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    created_at_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    created_at_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can view all users
):
    """
    Retrieve users with optional filtering.
    
    Supports filtering by various attributes including:
    - email: Filter by email address (exact match)
    - is_active: Filter by account status (true/false)
    - is_admin: Filter for admin users (true/false)
    - created_at_before: Filter for users created before specified datetime
    - created_at_after: Filter for users created after specified datetime
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin viewing user list with filters
    log_admin_action(
        user=current_user,
        action="view_all_users",
        email_filter=email,
        is_active_filter=is_active,
        is_admin_filter=is_admin,
        skip=skip,
        limit=limit
    )
    
    user_repo = UserRepository(db)
    
    # Build filter dictionary from provided parameters
    filters = {}
    if email is not None:
        filters["email"] = email
    if is_active is not None:
        filters["is_active"] = is_active
    if is_admin is not None:
        filters["is_admin"] = is_admin
        
    # Handle date range filters - these need special handling in the repository
    if created_at_before is not None:
        filters["created_at__lt"] = created_at_before
    if created_at_after is not None:
        filters["created_at__gt"] = created_at_after
    
    users = user_repo.get_multi(skip=skip, limit=limit, **filters)
    return users

@router.get("/{user_id}", response_model=UserRead)
async def read_user(
    user_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can view specific users
):
    """
    Get user by ID.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin viewing specific user details
    log_admin_action(
        user=current_user,
        action="view_user_details",
        target_user_id=str(user_id)
    )
    
    user_repo = UserRepository(db)
    user = user_repo.get(user_id)
    
    if not user:
        # Log attempted access to non-existent user
        log_admin_action(
            user=current_user,
            action="view_user_not_found",
            target_user_id=str(user_id)
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/me", response_model=UserRead)
async def read_current_user(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get current user information.
    Does not require email verification.
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log basic user info access
    log_user_activity(
        user=current_user,
        action="view_basic_user_info"
    )
    
    # Simply return the current user from the dependency
    return current_user

@router.get("/me/profile", response_model=UserRead)
async def read_current_user_profile(
    db: Session = Depends(deps.get_db),
    # Require email verification for accessing your own profile
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
    
    # Simply return the current user from the dependency
    return current_user
