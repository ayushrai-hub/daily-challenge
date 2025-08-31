"""
Maintenance tasks for cleaning up expired verification tokens.
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import delete, select, and_
from typing import Dict, Any, Optional, List

from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics
from app.db.database import SessionLocal
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.maintenance.token_cleanup.cleanup_expired_verification_tokens", queue="maintenance")
def cleanup_expired_verification_tokens(days_threshold: int = 7) -> Dict[str, Any]:
    """
    Delete expired verification tokens that are older than the threshold.
    
    This helps keep the database clean by removing tokens that are:
    1. Already expired (past the expiration date)
    2. Already used (is_used=True)
    3. Older than the days_threshold (default: 7 days)
    
    Args:
        days_threshold: Number of days after expiration to keep tokens before deletion
        
    Returns:
        Dict with results of the cleanup operation
    """
    logger.info(f"Starting cleanup of expired verification tokens (threshold: {days_threshold} days)")
    
    # Create database session
    db = SessionLocal()
    try:
        # Calculate cutoff date (tokens older than this will be deleted)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        # Find tokens to delete:
        # 1. Tokens that are expired AND older than cutoff_date
        # 2. Tokens that are used AND older than cutoff_date
        query = select(VerificationToken).where(
            and_(
                VerificationToken.created_at <= cutoff_date,
                (VerificationToken.is_used == True) | (VerificationToken.expires_at <= datetime.now(timezone.utc))
            )
        )
        
        # Execute query to get tokens for logging
        tokens_to_delete = db.execute(query).scalars().all()
        token_count = len(tokens_to_delete)
        
        if token_count > 0:
            # Log information about tokens being deleted
            token_ids = ", ".join(str(token.id) for token in tokens_to_delete[:5])
            logger.info(f"Deleting {token_count} expired verification tokens. Sample IDs: {token_ids}{'...' if token_count > 5 else ''}")
            
            # Delete the tokens
            delete_query = delete(VerificationToken).where(
                and_(
                    VerificationToken.created_at <= cutoff_date,
                    (VerificationToken.is_used == True) | (VerificationToken.expires_at <= datetime.now(timezone.utc))
                )
            )
            db.execute(delete_query)
            
            # Update verification metrics to track expired tokens
            try:
                # Get or create today's metrics
                metrics = VerificationMetrics.get_or_create_for_today(db=db)
                
                # Increment expired count for each token
                for _ in range(token_count):
                    metrics.update_verification_expired(db=db)
                
                logger.info(f"Updated verification metrics with {token_count} expired tokens")
            except Exception as e:
                logger.error(f"Error updating verification metrics: {str(e)}")
            
            # Commit all changes
            db.commit()
            
            logger.info(f"Successfully deleted {token_count} expired verification tokens")
            return {
                "success": True,
                "deleted_count": token_count,
                "threshold_days": days_threshold,
                "metrics_updated": True
            }
        else:
            logger.info("No expired verification tokens found for deletion")
            return {
                "success": True,
                "deleted_count": 0,
                "threshold_days": days_threshold
            }
    
    except Exception as e:
        logger.error(f"Error during verification token cleanup: {str(e)}")
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "threshold_days": days_threshold
        }
    finally:
        db.close()
