"""
Admin endpoints for viewing and managing email verification.
These endpoints are protected and only accessible to administrators.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.api import deps
from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics
from app.db.models.user import User
from app.utils.logging_utils import log_admin_action
import logging

# Configure standard logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/verification",
    tags=["admin"],  # Only use admin tag to prevent duplication in docs
    dependencies=[Depends(deps.get_current_admin_user)],  # Only admins can access
)


@router.get("/metrics")
async def get_verification_metrics(
    days: int = Query(7, description="Number of days to include in metrics"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get email verification metrics for the specified number of days.
    Only accessible by administrators.
    """
    # Log admin action for viewing verification metrics
    log_admin_action(
        user=current_user,
        action="view_verification_metrics",
        days_period=days
    )
    # Calculate date range
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    # Format dates as strings (YYYY-MM-DD)
    date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                 for i in range(days + 1)]
    
    # Query metrics for each day in range
    metrics_list = db.query(VerificationMetrics).filter(
        VerificationMetrics.date.in_(date_range)
    ).all()
    
    # Create lookup dict for easier access
    metrics_by_date = {m.date: m for m in metrics_list}
    
    # Build complete dataset with zeroes for missing days
    daily_metrics = []
    for date_str in date_range:
        metrics = metrics_by_date.get(date_str, None)
        if metrics:
            daily_metrics.append({
                "date": date_str,
                "sent": metrics.verification_requests_sent,
                "completed": metrics.verification_completed,
                "expired": metrics.verification_expired,
                "resend_requests": metrics.resend_requests,
                "avg_verification_time": metrics.avg_verification_time,
                "median_verification_time": metrics.median_verification_time,
                "min_verification_time": metrics.min_verification_time,
                "max_verification_time": metrics.max_verification_time
            })
        else:
            # No metrics for this day, add zeroes
            daily_metrics.append({
                "date": date_str,
                "sent": 0,
                "completed": 0,
                "expired": 0,
                "resend_requests": 0,
                "avg_verification_time": None,
                "median_verification_time": None,
                "min_verification_time": None,
                "max_verification_time": None
            })
    
    # Calculate aggregate metrics
    total_sent = sum(m.verification_requests_sent for m in metrics_list) if metrics_list else 0
    total_completed = sum(m.verification_completed for m in metrics_list) if metrics_list else 0
    total_expired = sum(m.verification_expired for m in metrics_list) if metrics_list else 0
    total_resend = sum(m.resend_requests for m in metrics_list) if metrics_list else 0
    
    # Calculate verification rate
    verification_rate = (total_completed / total_sent) * 100 if total_sent > 0 else 0
    
    # Calculate average verification time across all days
    valid_times = [m.avg_verification_time for m in metrics_list 
                  if m.avg_verification_time is not None]
    overall_avg_time = sum(valid_times) / len(valid_times) if valid_times else None
    
    return {
        "period_start": start_date.strftime("%Y-%m-%d"),
        "period_end": end_date.strftime("%Y-%m-%d"),
        "days": days,
        "daily_metrics": daily_metrics,
        "aggregates": {
            "total_sent": total_sent,
            "total_completed": total_completed,
            "total_expired": total_expired,
            "total_resend_requests": total_resend,
            "verification_rate": verification_rate,
            "avg_verification_time_seconds": overall_avg_time,
            "avg_verification_time_formatted": format_time_duration(overall_avg_time) if overall_avg_time else None
        }
    }


@router.get("/tokens/expired")
async def list_expired_tokens(
    days: int = Query(30, description="List tokens expired within the last N days"),
    limit: int = Query(50, description="Maximum number of tokens to return"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get a list of expired verification tokens.
    Only accessible by administrators.
    """
    # Log admin action for viewing expired tokens
    log_admin_action(
        user=current_user,
        action="view_expired_tokens",
        days_period=days,
        limit=limit
    )
    # Define cutoff date for expired tokens
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query expired but unused tokens
    expired_tokens = db.query(VerificationToken).filter(
        VerificationToken.is_used == False,
        VerificationToken.expires_at < datetime.utcnow(),
        VerificationToken.expires_at > cutoff_date
    ).order_by(desc(VerificationToken.expires_at)).limit(limit).all()
    
    return {
        "count": len(expired_tokens),
        "limit": limit,
        "days": days,
        "tokens": [
            {
                "id": str(token.id),
                "user_id": str(token.user_id),
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "token_type": token.token_type,
                "expired_for_hours": (datetime.utcnow().replace(tzinfo=token.expires_at.tzinfo) - token.expires_at).total_seconds() / 3600
            }
            for token in expired_tokens
        ]
    }


@router.post("/tokens/cleanup", status_code=status.HTTP_200_OK)
async def manual_token_cleanup(
    days_threshold: int = Query(7, description="Delete tokens older than N days"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Dict[str, Any]:
    """
    Manually trigger cleanup of expired verification tokens.
    Only accessible by administrators.
    """
    # Log admin action for manual token cleanup (this is a maintenance operation)
    log_admin_action(
        user=current_user,
        action="manual_token_cleanup",
        days_threshold=days_threshold
    )
    # Import the cleanup task
    from app.tasks.maintenance.token_cleanup import cleanup_expired_verification_tokens
    
    # Run the cleanup synchronously for immediate feedback
    result = cleanup_expired_verification_tokens(days_threshold=days_threshold)
    
    return {
        "message": "Token cleanup completed",
        "result": result
    }


@router.get("/unverified")
async def list_unverified_users(
    days: int = Query(30, description="List users registered within the last N days"),
    limit: int = Query(50, description="Maximum number of users to return"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get a list of users who have not verified their email.
    Only accessible by administrators.
    """
    # Log admin action for viewing unverified users list (contains sensitive user data)
    log_admin_action(
        user=current_user,
        action="list_unverified_users",
        days_period=days,
        limit=limit
    )
    # Define cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Query unverified users
    unverified_users = db.query(User).filter(
        User.is_email_verified == False,
        User.created_at > cutoff_date
    ).order_by(desc(User.created_at)).limit(limit).all()
    
    return {
        "count": len(unverified_users),
        "limit": limit,
        "days": days,
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "created_at": user.created_at,
                "days_since_registration": (datetime.utcnow().replace(tzinfo=None) - user.created_at.replace(tzinfo=None)).days
            }
            for user in unverified_users
        ]
    }


def format_time_duration(seconds: Optional[float]) -> Optional[str]:
    """Format seconds into a human-readable duration."""
    if seconds is None:
        return None
        
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"
