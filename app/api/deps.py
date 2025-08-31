from typing import Optional, Callable, Any
from datetime import datetime, timezone
import logging
from functools import wraps

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

from app.db.database import SessionLocal
from app.core.config import settings
from app.core.security import decode_token
from app.db.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import TokenPayload
from uuid import UUID
from app.core.middleware import user_id_ctx_var, user_email_ctx_var, user_is_admin_ctx_var

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Dependency to get database session
async def get_db() -> Session:
    """
    Dependency to get database session.
    
    This dependency:
    1. Creates a new database session
    2. Yields the session to the route handler
    3. Closes the session after the request is complete
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency to get the current authenticated user.
    
    Args:
        db: Database session
        token: JWT token from Authorization header
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # For test environment, check if this is a test token
    if settings.TESTING and token.startswith("test_token_"):
        # Test token format: test_token_<user_id>
        try:
            user_id = UUID(token.replace("test_token_", ""))
            user_repo = UserRepository(db)
            user = user_repo.get(user_id)
            if user is None:
                raise credentials_exception
            return user
        except (ValueError, TypeError):
            raise credentials_exception

    # Standard JWT token validation for non-test environments
    try:
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
    
    user_repo = UserRepository(db)
    
    # The token subject should always be a user ID
    try:
        user_id = UUID(token_data.sub)
        user = user_repo.get(user_id)
    except (ValueError, TypeError):
        # If we can't convert to UUID, consider it invalid
        raise credentials_exception
            
    if user is None:
        raise credentials_exception
    
    # Update last_login if it's been more than a day
    now = datetime.now(timezone.utc)
    if not user.last_login or (now - user.last_login.replace(tzinfo=timezone.utc)).days >= 1:
        user.last_login = now
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get the current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to get the current admin user.
    
    Args:
        current_user: Current active user
        
    Returns:
        Current admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user),
    bypass_verification: bool = False,
):
    """
    Gets the current user and validates that their email is verified.
    
    Args:
        current_user: The current active user
        bypass_verification: If True, verification check is bypassed
        
    Returns:
        User: The current verified user
        
    Raises:
        HTTPException: If the user's email is not verified
    """
    from app.core.config import settings
    import os
    
    # Check for bypass in environment variables directly as a more reliable method
    env_bypass = os.environ.get("BYPASS_EMAIL_VERIFICATION", "").lower() == "true"
    
    # Also check settings object as a fallback
    settings_bypass = getattr(settings, "BYPASS_EMAIL_VERIFICATION", False)
    
    # If either test mode is enabled, or explicit bypass is requested, skip verification
    if bypass_verification or env_bypass or settings_bypass or os.environ.get("TESTING", "").lower() == "true":
        return current_user
    
    # For production or when verification is enforced, check user's status
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please verify your email to access this resource.",
        )
    
    return current_user


def log_user_activity(request: Request = None):
    """
    Dependency that sets user context variables for logging.
    This should be included as a dependency in all authenticated endpoints.
    
    Args:
        request: The FastAPI request object (optional)
        
    Returns:
        A dependency function that captures the authenticated user
    """
    logger = logging.getLogger("app.api.deps")
    
    async def _log_user_activity(current_user: User = Depends(get_current_active_user)):
        """
        Sets context variables for the authenticated user.
        
        Args:
            current_user: The current authenticated user from dependency injection
        """
        # Set user context variables for logging
        if current_user:
            user_id = str(current_user.id) if hasattr(current_user, "id") else None
            user_email = current_user.email if hasattr(current_user, "email") else None
            is_admin = current_user.is_admin if hasattr(current_user, "is_admin") else False
            
            # Set context variables
            user_id_ctx_var.set(user_id)
            user_email_ctx_var.set(user_email)
            user_is_admin_ctx_var.set(is_admin)
            
            # Log detailed user activity if this is an admin
            if is_admin and request:
                logger.info(
                    f"Admin activity: {request.method} {request.url.path}", 
                    extra={
                        "user_id": user_id,
                        "user_email": user_email,
                        "is_admin": is_admin,
                        "admin_action": True
                    }
                )
        
        # Return the current user so this can be chained with other dependencies
        return current_user
    
    return _log_user_activity
