"""
Admin endpoints for tag normalization statistics.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, get_current_admin_user
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus
from app.db.models.user import User
from app.core.logging import get_logger

logger = get_logger()
router = APIRouter()


@router.get("/", response_model=Dict[str, Any])
async def get_tag_normalization_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get statistics about tag normalizations.
    Only accessible to admins.
    """
    # Query to get counts for different review statuses
    stats = db.query(
        func.count(TagNormalization.id).label("total"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.pending).label("pending"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.approved).label("approved"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.rejected).label("rejected"),
        func.count(TagNormalization.id).filter(
            (TagNormalization.review_status == TagReviewStatus.approved) & 
            (TagNormalization.source == "ai_generated")
        ).label("auto_approved")
    ).one()
    
    # Convert to dictionary
    return {
        "total": stats.total,
        "pending": stats.pending,
        "approved": stats.approved,
        "rejected": stats.rejected,
        "auto_approved": stats.auto_approved
    }
