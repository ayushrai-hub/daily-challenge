from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import func
import hmac
import hashlib
import json
import re
import logging

from app.db.session import get_db
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus
from app.db.models.email_queue import EmailQueue, EmailStatus
from app.db.models.user import User
from app.db.models.problem import Problem
from app.core.logging import get_logger
from app.core.config import settings
from app.api import deps

logger = get_logger()

router = APIRouter(tags=["webhooks"], prefix="/webhooks")

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify the webhook signature from Resend.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from the webhook request headers
        secret: Secret key for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not secret or not signature:
        return False
        
    computed_signature = hmac.new(
        key=secret.encode(),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, signature)

def extract_problem_id_from_url(url: str) -> Optional[str]:
    """Extract problem ID from URL if it's a problem URL."""
    # Match pattern for problem URL 
    pattern = r'/problem/([0-9a-f-]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None

@router.post("/resend", status_code=status.HTTP_200_OK)
async def resend_webhook(
    request: Request, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Handle webhooks from Resend email service.
    
    Updates email queue status and delivery logs based on email events:
    - email.sent: Mark email as sent in queue
    - email.delivered: Mark email as delivered and update delivery log
    - email.opened: Track when user opened the email
    - email.clicked: Track when user clicked a link in the email
    
    Returns:
        Dict with status information
    """
    # Get raw request body for signature verification
    body = await request.body()
    
    # Verify webhook signature if configured
    signature = request.headers.get("resend-signature")
    webhook_secret = getattr(settings, "RESEND_WEBHOOK_SECRET", None)
    
    if webhook_secret and signature:
        if not verify_signature(body, signature, webhook_secret):
            logger.warning("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
    
    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid JSON payload"
        )
    
    logger.info(f"Received Resend webhook: {payload}")
    
    # Extract event data
    event_type = payload.get("type")
    email_data = payload.get("data", {})
    email_id = email_data.get("email_id")
    
    if not event_type or not email_id:
        logger.warning("Missing event type or email ID in webhook")
        return {"status": "error", "message": "Invalid webhook payload"}
    
    # Extract recipient and subject from the event data
    recipient = email_data.get("to")
    subject = email_data.get("subject")
    
    if not recipient or not subject:
        logger.warning("Missing recipient or subject in webhook data")
        return {"status": "error", "message": "Missing recipient or subject"}
        
    # Try to identify which problem this email is about from the subject
    problem_id = None
    problem_title = None
    user_id = None
    
    # Check if this is a Daily Challenge email
    if "Daily Challenge:" in subject or "Challenge Solution:" in subject:
        # Extract problem title from subject
        if "Daily Challenge:" in subject:
            # Format: "Daily Challenge: <Problem Title>"
            problem_title = subject.split("Daily Challenge:", 1)[1].strip()
        elif "Challenge Solution:" in subject:
            # Format: "Challenge Solution: <Problem Title>"
            problem_title = subject.split("Challenge Solution:", 1)[1].strip()
            
        if problem_title:
            # Find the problem by title
            problem = db.query(Problem).filter(Problem.title == problem_title).first()
            if problem:
                problem_id = problem.id
                
        # Find the user by email
        user = db.query(User).filter(func.lower(User.email) == recipient.lower()).first()
        if user:
            user_id = user.id
    
    # If we have a click event, try to extract problem ID from URL
    if event_type == "email.clicked" and "url" in email_data:
        clicked_url = email_data.get("url")
        extracted_id = extract_problem_id_from_url(clicked_url)
        if extracted_id:
            # Validate that this is a valid UUID in our database
            problem_from_url = db.query(Problem).filter(Problem.id == extracted_id).first()
            if problem_from_url:
                problem_id = problem_from_url.id
                
    # If we don't have both user_id and problem_id, we can't update delivery logs
    if not user_id or not problem_id:
        logger.warning(f"Could not identify user or problem for email: {subject} to {recipient}")
        return {"status": "success", "message": "Email recorded but not linked to any delivery log"}
    
    # Now look for the delivery log
    delivery_log = (
        db.query(DeliveryLog)
        .filter(
            DeliveryLog.user_id == user_id,
            DeliveryLog.problem_id == problem_id
        )
        .order_by(DeliveryLog.created_at.desc())
        .first()
    )
    
    if not delivery_log:
        logger.warning(f"No delivery log found for user {user_id} and problem {problem_id}")
        return {"status": "success", "message": "Email event recorded but no matching delivery log found"}
    
    # Update delivery log based on event type
    now = datetime.utcnow()
    
    if event_type == "email.delivered":
        delivery_log.status = DeliveryStatus.delivered
        delivery_log.delivered_at = now
        logger.info(f"Updated delivery log for problem {problem_id} to user {user_id} as delivered")
        
    elif event_type == "email.opened":
        # Only update opened_at if not already set
        if not delivery_log.opened_at:
            delivery_log.opened_at = now
            if delivery_log.status == DeliveryStatus.scheduled:
                delivery_log.status = DeliveryStatus.opened
            logger.info(f"Updated delivery log for problem {problem_id} as opened by user {user_id}")
        
    elif event_type == "email.clicked":
        # Update meta information with click data
        meta = delivery_log.meta or {}
        clicks = meta.get("clicks", 0)
        meta["clicks"] = clicks + 1
        meta["last_clicked_at"] = now.isoformat()
        
        # Record the URL that was clicked if available
        if "url" in email_data:
            click_urls = meta.get("click_urls", [])
            click_urls.append({
                "url": email_data["url"],
                "clicked_at": now.isoformat()
            })
            meta["click_urls"] = click_urls
        
        delivery_log.meta = meta
        
        # Mark as completed if the user clicked a solve/view button
        clicked_url = email_data.get("url", "")
        if not delivery_log.completed_at and ("solve" in clicked_url.lower() or "/problem/" in clicked_url.lower()):
            delivery_log.completed_at = now
            delivery_log.status = DeliveryStatus.completed
            logger.info(f"Marked delivery log for problem {problem_id} as completed by user {user_id}")
    
    elif event_type in ["email.bounced", "email.failed"]:
        delivery_log.status = DeliveryStatus.failed
        # Store failure details in meta
        meta = delivery_log.meta or {}
        meta["failure_reason"] = email_data.get("reason", "Unknown reason")
        meta["failed_at"] = now.isoformat()
        delivery_log.meta = meta
        logger.warning(f"Delivery log for problem {problem_id} to user {user_id} marked as failed")
    
    # Commit all changes
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Processed {event_type} event for email {email_id}"
    }
