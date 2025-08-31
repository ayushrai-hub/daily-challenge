from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List
from app.schemas.email import EmailCreate, EmailRead
from app.services.email.queue_service import EmailQueueService
from app.db.session import get_db
from app.db.models.email_queue import EmailQueue
from app.db.models.user import User
from app.api import deps
from app.utils.logging_utils import log_admin_action, log_user_activity
import logging

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email-queue", tags=["Email Queue"])

@router.post("/", response_model=EmailRead, status_code=status.HTTP_201_CREATED)
def enqueue_email(
    email: EmailCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin access
):
    # Log admin action for sending email
    log_admin_action(
        user=current_user,
        action="enqueue_email",
        recipient=email.recipient,
        subject=email.subject,
        template=email.template if hasattr(email, 'template') else None
    )
    
    # Process the email enqueue operation
    try:
        result = EmailQueueService.enqueue_email(db, email)
        logger.info(f"Email successfully queued to {email.recipient}")
        return result
    except Exception as e:
        logger.error(f"Failed to enqueue email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enqueueing email: {str(e)}"
        )

@router.get("/", response_model=List[EmailRead])
def get_email_queue(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin access
):
    # Log admin action for viewing email queue
    log_admin_action(
        user=current_user,
        action="view_email_queue",
        skip=skip,
        limit=limit
    )
    
    try:
        return EmailQueueService.get_queue(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"Error retrieving email queue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error retrieving email queue: {str(e)}"
        )

@router.get("/{email_id}", response_model=EmailRead)
def get_email_by_id(
    email_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin access
):
    # Log admin action for viewing specific email
    log_admin_action(
        user=current_user,
        action="view_email_details",
        email_id=str(email_id)
    )
    
    try:
        email = EmailQueueService.get_by_id(db, email_id)
        if not email:
            # Log not found event
            logger.warning(f"Admin attempted to view non-existent email: {email_id}")
            raise HTTPException(status_code=404, detail="Email not found")
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving email {email_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving email: {str(e)}"
        )

@router.patch("/{email_id}/status", response_model=EmailRead)
def update_email_status(
    email_id: UUID, 
    status: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin access
):
    # Log admin action for updating email status
    log_admin_action(
        user=current_user,
        action="update_email_status",
        email_id=str(email_id),
        new_status=status
    )
    
    try:
        email = EmailQueueService.update_status(db, email_id, status)
        if not email:
            # Log not found event
            logger.warning(f"Admin attempted to update non-existent email: {email_id}")
            raise HTTPException(status_code=404, detail="Email not found")
            
        # Log successful status update
        logger.info(f"Email {email_id} status updated to '{status}' by admin {current_user.email}")
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email {email_id} status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating email status: {str(e)}"
        )

@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_email(
    email_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin access
):
    # First log admin action for email deletion attempt
    log_admin_action(
        user=current_user,
        action="delete_email",
        email_id=str(email_id)
    )
    
    # Get the email first to include details in logs if available
    try:
        email = EmailQueueService.get_by_id(db, email_id)
        if email:
            # Add extra logging with email details before deletion
            logger.info(
                f"Admin {current_user.email} deleting email {email_id}", 
                extra={
                    "recipient": getattr(email, 'recipient', 'unknown'),
                    "subject": getattr(email, 'subject', 'unknown'),
                    "status": getattr(email, 'status', 'unknown')
                }
            )
    except Exception:
        # Don't fail the delete operation if we can't get details
        pass
        
    try:
        success = EmailQueueService.delete(db, email_id)
        if not success:
            logger.warning(f"Admin attempted to delete non-existent email: {email_id}")
            raise HTTPException(status_code=404, detail="Email not found")
            
        # Log successful deletion
        logger.info(f"Email {email_id} successfully deleted by admin {current_user.email}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email {email_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting email: {str(e)}"
        )
