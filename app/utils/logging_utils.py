"""
Logging utilities for tracking user activity and admin actions.
Provides simple, standardized logging across the application.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request
from app.db.models.user import User

# Get context variables from middleware
from app.core.middleware import (
    user_id_ctx_var,
    user_email_ctx_var,
    user_is_admin_ctx_var,
    request_id_ctx_var,
    get_request_id
)


def set_user_context(user: User, request: Optional[Request] = None) -> Dict[str, Any]:
    """
    Set user context variables for logging.
    
    Args:
        user: The authenticated user
        request: Optional FastAPI request object
        
    Returns:
        Dict containing user context fields
    """
    # Ensure we have a valid request ID
    request_id = get_request_id()
    if not request_id:
        # Generate a new request ID if none exists
        request_id = str(uuid.uuid4())
        request_id_ctx_var.set(request_id)
    
    # Extract user information
    user_id = str(user.id) if hasattr(user, "id") else None
    user_email = user.email if hasattr(user, "email") else None
    is_admin = user.is_admin if hasattr(user, "is_admin") else False
    
    # Set context variables for request logging
    user_id_ctx_var.set(user_id)
    user_email_ctx_var.set(user_email)
    user_is_admin_ctx_var.set(is_admin)
    
    # Return user context dict for use in log extras
    return {
        "request_id": request_id,
        "user_id": user_id,
        "user_email": user_email,
        "is_admin": is_admin,
        "timestamp": datetime.utcnow().isoformat()
    }


def log_user_activity(user: User, action: str, **context) -> None:
    """
    Log general user activity with user context.
    
    Args:
        user: The authenticated user
        action: Name of the action being performed
        **context: Additional context to include in logs
    """
    # Set user context variables for logging
    user_context = set_user_context(user)
    
    # Get logger
    logger = logging.getLogger("app.api.user_activity")
    
    # Log user activity
    logger.info(
        f"User activity: {action}",
        extra={
            **user_context,
            "action": action,
            **context
        }
    )


def log_admin_action(user: User, action: str, **context) -> None:
    """
    Log detailed admin action with user context and additional context.
    
    Args:
        user: The admin user
        action: Name of the admin action being performed
        **context: Additional context for the admin action
    """
    # Check if user is actually an admin
    is_admin = user.is_admin if hasattr(user, "is_admin") else False
    if not is_admin:
        logging.getLogger("app.api.admin_audit").warning(
            f"Non-admin user attempted admin action: {action}",
            extra={"user_id": str(user.id), "user_email": user.email}
        )
        return
    
    # Set user context variables for logging
    user_context = set_user_context(user)
    
    # Get admin audit logger
    logger = logging.getLogger("app.api.admin_audit")
    
    # Log the admin action
    logger.info(
        f"Admin action: {action}",
        extra={
            **user_context,
            "admin_action": action,
            **context
        }
    )


def log_security_event(user: Optional[User], action: str, is_success: bool = True, **context) -> None:
    """
    Log security-related events like login attempts and password changes.
    
    Args:
        user: Optional authenticated user (may be None for login failures)
        action: Name of the security action (login, password_change, etc.)
        is_success: Whether the security operation succeeded
        **context: Additional context for the security event
    """
    # Get the security logger
    logger = logging.getLogger("app.security")
    
    # Create context dict
    log_context = {
        "action": action,
        "success": is_success,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": get_request_id() or str(uuid.uuid4()),
        **context
    }
    
    # Add user context if available
    if user:
        log_context.update({
            "user_id": str(user.id),
            "user_email": user.email,
            "is_admin": user.is_admin if hasattr(user, "is_admin") else False
        })
    
    # Log at appropriate level
    if is_success:
        logger.info(f"Security event: {action}", extra=log_context)
    else:
        logger.warning(f"Security event: {action}", extra=log_context)
