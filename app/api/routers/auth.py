from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.api import deps
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_password_hash,
    verify_password
)
from app.repositories.user import UserRepository
from app.db.models.user import User
from app.schemas.user import UserCreate, UserRead, Token, PasswordResetRequest, PasswordReset, PasswordChange
from app.schemas.email import EmailVerificationRequest
from app.core.rate_limiter import rate_limit
from fastapi.encoders import jsonable_encoder
from app.tasks.email.send_email import send_verification_email
from app.tasks.email.send_password_reset_email import send_password_reset_email
from app.db.models.verification_token import VerificationToken
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.verification_metrics import VerificationMetrics
import logging

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)

@router.get("/admin-check", response_model=dict)
async def check_admin_status(
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Check if the current user has admin privileges.
    Returns a simple dict with is_admin boolean.
    """
    return {
        "is_admin": current_user.is_admin,
        "email": current_user.email,
        "full_name": current_user.full_name
    }

@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@rate_limit(limit_value=settings.RATE_LIMIT_REGISTER)  # Use rate limit from settings
def register(
    request: Request,  # Required for rate limiting
    background_tasks: BackgroundTasks,
    *,
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Register a new user and send verification email.
    """
    # Create logger for registration
    logger = logging.getLogger("app.api.auth")
    client_ip = request.client.host if request.client else "unknown"
    
    # Log registration attempt with masked password for security
    logger.info(
        "User registration attempt",
        extra={
            "email": user_in.email,
            "ip_address": client_ip,
            "has_full_name": bool(user_in.full_name)
        }
    )
    
    user_repo = UserRepository(db)
    
    # Check if user with this email already exists
    if user_repo.get_by_email(email=user_in.email):
        # Log duplicate registration attempt
        logger.warning(
            "Registration failed: Email already exists",
            extra={
                "email": user_in.email,
                "ip_address": client_ip,
                "reason": "duplicate_email"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )
    
    # Create new user with hashed password
    user_data = user_in.dict(exclude={"password"})
    user_data["hashed_password"] = get_password_hash(user_in.password)
    user_data["is_email_verified"] = False  # Explicit set to false
    
    # Ensure full_name is properly set and logged
    logger.info(
        "User data before creation",
        extra={
            "email": user_in.email,
            "full_name_in_request": user_in.full_name,
            "full_name_in_data": user_data.get("full_name")
        }
    )
    
    # Make sure full_name is explicitly set if provided
    if user_in.full_name:
        user_data["full_name"] = user_in.full_name
        # Log that we're setting the full_name explicitly
        logger.info(
            "Setting full_name explicitly",
            extra={
                "full_name": user_in.full_name,
                "user_data": user_data
            }
        )
    
    # Create the user
    user = user_repo.create(obj_in=user_data)
    
    # Verify if full_name was actually saved
    logger.info(
        "User created - verifying full_name was saved",
        extra={
            "user_id": str(user.id),
            "saved_full_name": user.full_name,
            "email": user.email
        }
    )
    
    # Create verification token
    verification_token = VerificationToken.create_token(
        db=db,
        user_id=user.id
    )
    
    # Track verification metrics
    metrics = VerificationMetrics.get_or_create_for_today(db)
    metrics.update_verification_sent(db)
    
    # Send verification email asynchronously
    background_tasks.add_task(
        send_verification_email,
        user_id=str(user.id),
        email=user.email,
        name=user.full_name or "User",
        token=verification_token.token
    )
    
    # Log successful registration
    logger.info(
        "User registration successful",
        extra={
            "user_id": str(user.id),
            "email": user.email,
            "ip_address": client_ip,
            "verification_sent": True
        }
    )
    
    return user


@router.post("/login", response_model=Token)
@rate_limit(limit_value=settings.RATE_LIMIT_LOGIN)  # Use rate limit from settings
def login(
    request: Request,  # Required for rate limiting
    *,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    # Import security logging utility
    from app.utils.logging_utils import log_security_event
    
    # Get client IP for security logging
    client_ip = request.client.host if request.client else "unknown"
    
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email=form_data.username)
    
    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Log failed login attempt with standard security logging
        log_security_event(
            user=None,  # No valid user for failed login
            action="login",
            is_success=False,
            user_email=form_data.username,  # Track attempted email
            ip_address=client_ip,
            reason="invalid_credentials"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Check if user is active
    if not user.is_active:
        # Log inactive account login attempt
        log_security_event(
            user=user,
            action="login",
            is_success=False,
            reason="inactive_account",
            ip_address=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
        )
        
    # Inform unverified users that they need to verify their email
    # but still allow login - more restrictive checks can be in protected endpoints
    email_verification_required = not user.is_email_verified
    
    # Create access token with user ID as subject
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),  # Ensure user ID is a string for consistency
        expires_delta=access_token_expires
    )
    
    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    
    # Log successful login with standard security logging
    log_security_event(
        user=user,
        action="login",
        is_success=True,
        ip_address=client_ip
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "email_verification_required": email_verification_required,
        "is_admin": user.is_admin,
        "email": user.email,
        "full_name": user.full_name
    }


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log user activity
    log_user_activity(
        user=current_user,
        action="read_user_profile"
    )
    
    try:
        return current_user
    except Exception as e:
        # Log errors in user model mapping
        logging.error(f"Error in /me endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user data"
        )


@router.post("/verify-email/{token}", status_code=status.HTTP_200_OK)
@rate_limit(limit_value="5/minute")
def verify_email(
    request: Request,
    token: str,
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Verify a user's email using the token sent to their email address.
    """
    # Create standardized logger for verification
    logger = logging.getLogger("app.api.auth")
    client_ip = request.client.host if request.client else "unknown"
    
    # Log verification attempt without exposing full token
    logger.info(
        "Email verification attempt",
        extra={
            "token_prefix": token[:4] if len(token) > 4 else "<short>",  # Only log prefix for security
            "ip_address": client_ip
        }
    )
    
    # Validate the token
    user_id = VerificationToken.validate_token(
        db=db,
        token_value=token,
        token_type="email_verification"
    )
    
    if not user_id:
        # Log invalid token with structured logging
        logger.warning(
            "Email verification failed: Invalid token",
            extra={
                "token_prefix": token[:4] if len(token) > 4 else "<short>",
                "ip_address": client_ip,
                "reason": "invalid_token"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Mark token as used
    token_data = VerificationToken.mark_as_used(db, token)
    
    # Get the user and mark as verified
    user_repo = UserRepository(db)
    user = user_repo.get(id=user_id)
    
    if not user:
        # Log user not found with structured logging
        logger.warning(
            "Email verification failed: User not found",
            extra={
                "user_id": str(user_id),
                "ip_address": client_ip,
                "reason": "user_not_found"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user verification status
    user.is_email_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Track verification metrics
    metrics = VerificationMetrics.get_or_create_for_today(db)
    
    # Calculate verification time if we have both timestamps
    verification_time_seconds = None
    if token_data and token_data.created_at:
        # Calculate seconds between token creation and verification
        time_diff = datetime.now(timezone.utc) - token_data.created_at.replace(tzinfo=timezone.utc)
        verification_time_seconds = time_diff.total_seconds()
        
    metrics.update_verification_completed(db, verification_time_seconds)
    
    # Log successful verification
    logger.info(
        "Email verification successful",
        extra={
            "user_id": str(user.id),
            "email": user.email,
            "ip_address": client_ip,
            "verification_time_seconds": verification_time_seconds,
            "days_since_registration": (datetime.now(timezone.utc) - user.created_at).days if user.created_at else None
        }
    )
    
    return {
        "success": True,
        "user_id": str(user_id),
        "email": user.email,
        "status": "verified"
    }


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
@rate_limit(limit_value="3/minute")
def resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Resend email verification link to the current user.
    """
    # Check if email is already verified
    if current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Check if user has requested a token within the cooldown period (5 minutes)
    cooldown_minutes = 5
    recent_token = VerificationToken.check_recent_token(
        db=db,
        user_id=current_user.id,
        minutes=cooldown_minutes
    )
    
    if recent_token and not recent_token.is_used:
        # Format time remaining in readable format
        time_since_creation = datetime.now(timezone.utc) - recent_token.created_at.replace(tzinfo=timezone.utc)
        cooldown_seconds = cooldown_minutes * 60
        seconds_remaining = cooldown_seconds - time_since_creation.total_seconds()
        
        if seconds_remaining > 0:
            minutes_remaining = int(seconds_remaining // 60)
            seconds_left = int(seconds_remaining % 60)
            
            # Track rate limit hit in metrics
            metrics = VerificationMetrics.get_or_create_for_today(db)
            metrics.update_resend_requests(db)  # Still counts as an attempt
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {minutes_remaining}m {seconds_left}s before requesting another verification email"
            )
    
    # Create a new verification token
    verification_token = VerificationToken.create_token(
        db=db,
        user_id=current_user.id
    )
    
    # Track metrics for resend request
    metrics = VerificationMetrics.get_or_create_for_today(db)
    metrics.update_resend_requests(db)
    metrics.update_verification_sent(db)  # Also counts as a verification sent
    
    # Send verification email asynchronously
    background_tasks.add_task(
        send_verification_email,
        user_id=str(current_user.id),
        email=current_user.email,
        name=current_user.full_name or "User",
        token=verification_token.token
    )
    
    return {
        "message": "Verification email sent successfully",
        "email": current_user.email,
        "status": "pending"
    }


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
@rate_limit(limit_value="3/minute")
async def request_password_reset(
    request: Request,
    background_tasks: BackgroundTasks,
    password_reset: PasswordResetRequest,
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Request a password reset token sent to the user's email.
    """
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(email=password_reset.email)
    
    # Always return success even if user doesn't exist for security reasons
    if not user:
        logger.info(f"Password reset requested for non-existent email: {password_reset.email}")
        return {
            "message": "If a user with this email exists, a password reset link has been sent.",
            "status": "pending"
        }
    
    # Check if user is active
    if not user.is_active:
        logger.info(f"Password reset requested for inactive user: {password_reset.email}")
        return {
            "message": "If a user with this email exists, a password reset link has been sent.",
            "status": "pending"
        }
    
    # Check if user has requested a token within the cooldown period
    cooldown_minutes = 5
    recent_token = PasswordResetToken.check_recent_token(
        db=db,
        user_id=user.id,
        minutes=cooldown_minutes
    )
    
    if recent_token and not recent_token.is_used:
        # For security reasons, don't disclose that a token was already requested
        logger.info(f"Password reset cooldown in effect for: {password_reset.email}")
        return {
            "message": "If a user with this email exists, a password reset link has been sent.",
            "status": "pending"
        }
    
    # Create a new password reset token
    reset_token = PasswordResetToken.create_token(
        db=db,
        user_id=user.id,
        expiration_hours=1  # Password reset tokens expire after 1 hour for security
    )
    
    # Send password reset email asynchronously
    background_tasks.add_task(
        send_password_reset_email,
        user_id=str(user.id),
        email=user.email,
        name=user.full_name or "User",
        token=reset_token.token
    )
    
    return {
        "message": "If a user with this email exists, a password reset link has been sent.",
        "status": "pending"
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@rate_limit(limit_value="3/minute")
async def reset_password(
    request: Request,
    password_reset: PasswordReset,
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Reset user password using the token sent to their email.
    """
    # Validate the token and get user ID
    user_id = PasswordResetToken.validate_token(
        db=db,
        token_value=password_reset.token,
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
    
    # Mark token as used
    PasswordResetToken.mark_as_used(db, password_reset.token)
    
    # Get the user
    user_repo = UserRepository(db)
    user = user_repo.get(id=user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update user's password
    user.hashed_password = get_password_hash(password_reset.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Password has been reset successfully.",
        "status": "success"
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
@rate_limit(limit_value="5/minute")
async def change_password(
    request: Request,
    password_change: PasswordChange,
    current_user: User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Change user password while logged in.
    Requires the current password for verification.
    """
    logger = logging.getLogger("app.api.auth")
    
    # Import the standard logging utility
    from app.utils.logging_utils import log_security_event
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        # Log failed password change with standard security logging
        log_security_event(
            user=current_user,
            action="password_change",
            is_success=False,
            reason="invalid_current_password"
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update user's password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # Log successful password change with standard security logging
    log_security_event(
        user=current_user,
        action="password_change",
        is_success=True
    )
    
    return {
        "message": "Password has been changed successfully.",
        "status": "success"
    }
