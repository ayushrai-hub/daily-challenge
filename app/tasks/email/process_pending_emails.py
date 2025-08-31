import asyncio

"""
Email processing tasks for the Daily Challenge application.
Handles scheduled delivery of pending emails.
"""
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from typing import Dict, List, Any, Optional, Tuple
import time
from celery.exceptions import Retry
from sqlalchemy import text, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import SessionLocal
from datetime import datetime, timedelta

logger = get_logger()

from app.db.models.email_queue import EmailQueue, EmailStatus
from app.services.email.email_service import EmailService


# Maximum number of retry attempts for failed emails
MAX_RETRY_COUNT = 3

# How many emails to process in a single batch
BATCH_SIZE = 50

# How long to wait before retrying a failed email (in minutes)
RETRY_DELAYS = [5, 30, 120]  # 5 min, 30 min, 2 hours


@celery_app.task(
    name="app.tasks.email.process_pending_emails.process_pending_emails", 
    queue="emails",
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def process_pending_emails(self) -> Dict[str, Any]:
    """
    Query the database for pending emails, send them, and update their status.
    
    This task processes emails in the following order:
    1. Emails scheduled for immediate delivery (scheduled_for <= now)
    2. Emails that have previously failed but are eligible for retry
    
    Returns:
        Dictionary with processing results
    """
    logger.info("Processing pending emails")
    processed_count = 0
    failed_count = 0
    retry_count = 0
    skipped_count = 0
    now = datetime.utcnow()
    
    try:
        with SessionLocal() as db:
            # Find emails that are either:
            # 1. Pending and scheduled for now or earlier
            # 2. Failed but with retry count < MAX_RETRY_COUNT and last retry time > delay
            query = db.query(EmailQueue).filter(
                or_(
                    # Pending emails scheduled for now or earlier
                    and_(
                        EmailQueue.status == EmailStatus.pending,
                        EmailQueue.scheduled_for <= now
                    ),
                    # Failed emails eligible for retry
                    and_(
                        EmailQueue.status == EmailStatus.failed,
                        EmailQueue.retry_count < MAX_RETRY_COUNT,
                        EmailQueue.last_retry_at.is_(None) | (EmailQueue.last_retry_at <= (now - timedelta(minutes=5)))
                    )
                )
            ).order_by(EmailQueue.scheduled_for).limit(BATCH_SIZE)
            
            pending_emails = query.all()
            logger.info(f"Found {len(pending_emails)} emails to process")
            
            for email in pending_emails:
                # Run the async function using asyncio.run since we're in a sync context
                success, retrying = asyncio.run(process_single_email(db, email, now))
                if success:
                    processed_count += 1
                elif retrying:
                    retry_count += 1
                else:
                    failed_count += 1
                    
            # Commit all changes at once
            db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error while processing emails: {str(e)}")
        # Retry the entire task if database error occurs
        raise self.retry(exc=e, countdown=60)
    except Exception as e:
        logger.error(f"Unexpected error in process_pending_emails: {str(e)}")
        raise
    
    logger.info(f"Email processing summary: {processed_count} sent, {retry_count} retrying, {failed_count} failed, {skipped_count} skipped")
    return {
        "success": True,
        "processed_count": processed_count,
        "retry_count": retry_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def process_single_email(db, email: EmailQueue, now: datetime) -> Tuple[bool, bool]:
    """
    Process a single email and update its status.
    
    Args:
        db: Database session
        email: EmailQueue object to process
        now: Current datetime
        
    Returns:
        Tuple of (success, retrying)
            - success: True if email was sent successfully
            - retrying: True if email failed but will be retried
    """
    # Initialize response values
    success = False
    retrying = False
    
    # Check if this is a retry and increment the counter
    if email.status == EmailStatus.failed:
        email.retry_count = (email.retry_count or 0) + 1
        email.last_retry_at = now
        logger.info(f"Retrying email {email.id}, attempt {email.retry_count} of {MAX_RETRY_COUNT}")
    
    try:
        # Use the template data if available, otherwise use the direct content
        if email.template_id and email.template_data:
            logger.debug(f"Using template {email.template_id} for email {email.id}")
            # Here we would use a template service to render the template
            # For now, we'll just use the stored content
            result = await EmailService.send_email(
                to=email.recipient,
                subject=email.subject,
                html=email.html_content,
                text=email.text_content,
                from_email=None,  # Use default from email
                force_send=True   # Force send since this is from the queue
            )
        else:
            # Send directly using stored content
            result = await EmailService.send_email(
                to=email.recipient,
                subject=email.subject,
                html=email.html_content,
                text=email.text_content,
                from_email=None,  # Use default from email
                force_send=True   # Force send since this is from the queue
            )
        
        # Check for success or validation failure
        if result and isinstance(result, dict):
            # Check for known error patterns in the response
            error_indicators = [
                result.get("status", "").startswith("validation_failed"),
                result.get("message", "").startswith("Invalid"),
                result.get("success") is False,
                "error" in result
            ]
            
            if any(error_indicators):
                error_msg = result.get("message", result.get("error", "Unknown API error"))
                raise Exception(f"Email API error: {error_msg}")
            
            # If we got here, consider it a success
            email.status = EmailStatus.sent
            email.sent_at = now
            email.delivery_data = result  # Store the delivery response
            success = True
            logger.info(f"Email {email.id} sent successfully to {email.recipient}")
    except Exception as e:
        logger.error(f"Failed to send email {email.id} to {email.recipient}: {str(e)}")
        email.error_message = str(e)
        
        # Determine if we should retry or mark as permanently failed
        if email.retry_count is None:
            email.retry_count = 1
        
        if email.retry_count < MAX_RETRY_COUNT:
            # Calculate next retry time based on retry count
            retry_delay_minutes = RETRY_DELAYS[min(email.retry_count - 1, len(RETRY_DELAYS) - 1)]
            email.scheduled_for = now + timedelta(minutes=retry_delay_minutes)
            email.last_retry_at = now
            email.status = EmailStatus.pending  # Keep as pending for retry
            retrying = True
            logger.info(f"Email {email.id} will be retried in {retry_delay_minutes} minutes")
        else:
            # Max retries reached, mark as permanently failed
            email.status = EmailStatus.failed
            logger.warning(f"Email {email.id} permanently failed after {email.retry_count} attempts")
    
    return success, retrying
    