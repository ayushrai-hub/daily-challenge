"""
Admin endpoints for dashboard statistics and information.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_admin_user
from app.db.models.tag import Tag
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus
from app.db.models.problem import Problem, ProblemStatus
from app.db.models.user import User
from app.core.logging import get_logger
from app.utils.logging_utils import log_admin_action  # Add enhanced logging utility

logger = get_logger()
router = APIRouter()


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get overall statistics for the admin dashboard.
    Returns counts and summaries for tags, problems, and users.
    Only accessible to admins.
    """
    # Log admin dashboard access
    log_admin_action(
        user=current_user,
        action="view_admin_dashboard"
    )
    
    # Get tag statistics
    total_tags = db.query(func.count(Tag.id)).scalar() or 0
    tag_categories = db.query(func.count(Tag.id)).filter(Tag.tag_type.isnot(None)).scalar() or 0
    
    # Get tag normalization statistics
    tag_normalizations = db.query(
        func.count(TagNormalization.id).label("total"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.pending).label("pending"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.approved).label("approved"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.rejected).label("rejected")
    ).one()
    
    # Get problem statistics
    problem_stats = db.query(
        func.count(Problem.id).label("total"),
        func.count(Problem.id).filter(Problem.status == ProblemStatus.approved).label("published"),
        func.count(Problem.id).filter(Problem.status == ProblemStatus.draft).label("draft"),
        func.count(Problem.id).filter(Problem.status == ProblemStatus.archived).label("archived")
    ).one()
    
    # Get user statistics
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    admin_users = db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0
    
    return {
        "tags": {
            "total": total_tags,
            "pending": tag_normalizations.pending,
            "categories": tag_categories
        },
        "problems": {
            "total": problem_stats.total,
            "pending": problem_stats.draft,
            "published": problem_stats.published
        },
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users
        }
    }
