"""
Daily Challenge scheduling tasks.

These tasks handle scheduling and delivery of daily challenges and their solutions.
"""
import asyncio
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.daily_challenge.challenge_service import DailyChallengeService
from datetime import datetime, timedelta
from typing import Dict, Any

logger = get_logger()

@celery_app.task(
    name="app.tasks.daily_challenge.schedule_challenges.schedule_daily_problems",
    queue="content",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def schedule_daily_problems(self, delivery_hour: int = 8) -> Dict[str, Any]:
    """
    Schedule daily problems for all eligible users.
    
    Args:
        delivery_hour: Hour of day to deliver challenges (0-23)
        
    Returns:
        Dictionary with results summary
    """
    logger.info(f"Running daily problem scheduling task (delivery hour: {delivery_hour})")
    
    try:
        with SessionLocal() as db:
            # Run the async function using asyncio.run since we're in a sync context
            results = asyncio.run(DailyChallengeService.schedule_daily_challenges(db, delivery_hour))
            
            logger.info(f"Daily problem scheduling completed: {results['scheduled']} scheduled, "
                      f"{results['skipped']} skipped, {results['errors']} errors")
            
            return {
                "success": True,
                "task": "schedule_daily_problems",
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }
    except Exception as e:
        logger.error(f"Error in schedule_daily_problems task: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    name="app.tasks.daily_challenge.schedule_challenges.schedule_pending_solutions", 
    queue="content",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def schedule_pending_solutions(self) -> Dict[str, Any]:
    """
    Schedule solution emails for problems that were delivered ~24 hours ago.
    
    Returns:
        Dictionary with results summary
    """
    logger.info("Running solution scheduling task")
    
    try:
        with SessionLocal() as db:
            results = asyncio.run(DailyChallengeService.schedule_pending_solutions(db))
            
            logger.info(f"Solution scheduling completed: {results['scheduled']} scheduled, "
                      f"{results['skipped']} skipped, {results['errors']} errors")
            
            return {
                "success": True,
                "task": "schedule_pending_solutions",
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }
    except Exception as e:
        logger.error(f"Error in schedule_pending_solutions task: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    name="app.tasks.daily_challenge.schedule_challenges.process_challenge_queue", 
    queue="emails",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def process_challenge_queue(self) -> Dict[str, Any]:
    """
    Process the challenge email queue and send out scheduled emails.
    
    Returns:
        Dictionary with processing results
    """
    logger.info("Processing challenge email queue")
    
    try:
        with SessionLocal() as db:
            results = asyncio.run(DailyChallengeService.process_email_queue(db))
            
            logger.info(f"Challenge email processing completed: {results['sent']} sent, "
                      f"{results['failed']} failed")
            
            return {
                "success": True,
                "task": "process_challenge_queue",
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }
    except Exception as e:
        logger.error(f"Error in process_challenge_queue task: {str(e)}")
        raise self.retry(exc=e, countdown=60)
