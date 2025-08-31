"""
Task to send password reset emails.
"""
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.config import get_settings
from app.services.email.queue_service import EmailQueueService
from app.services.email.templates import get_password_reset_template
from app.schemas.email import EmailCreate
from app.db.session import SessionLocal

settings = get_settings()
logger = get_logger()

@celery_app.task(name="app.tasks.email.send_password_reset_email.send_password_reset_email", queue="emails")
def send_password_reset_email(
    user_id: str,
    email: str,
    name: str,
    token: str
) -> Dict[str, Any]:
    """Enqueue a password reset email for a user.

    Args:
        user_id: ID of the user requesting password reset
        email: Email address of the user
        name: Full name of the user
        token: Password reset token

    Returns:
        Dictionary with status of the enqueue operation
    """
    logger.info(f"Enqueueing password reset email to {email} (User ID: {user_id})")

    try:
        # Generate the password reset link
        frontend_url = settings.FRONTEND_URL.rstrip('/')
        reset_link = f"{frontend_url}/reset-password/{token}"

        # Generate email content
        subject = "Password Reset Request - Daily Challenge"
        html_content = get_password_reset_template(
            user_name=name,
            reset_link=reset_link,
            token=token
        )

        # Create the email data
        email_data = EmailCreate(
            user_id=user_id,
            email_type="password_reset",
            recipient=email,
            subject=subject,
            html_content=html_content,
            text_content=f"Password Reset Request - Use this link to reset your password: {reset_link}",
            template_id="password_reset_email",
            template_data={
                "user_name": name,
                "reset_link": reset_link,
                "token": token
            }
        )

        # Enqueue the email
        with SessionLocal() as db:
            result = EmailQueueService.enqueue_email(db=db, email_data=email_data)

        logger.info(f"Password reset email enqueued for {email}, ID: {result.id}")
        return {
            "success": True,
            "message": f"Password reset email enqueued for {email}",
            "user_id": str(user_id),
            "email_id": str(result.id),
            "email_type": "password_reset"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue password reset email for {email}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to enqueue password reset email: {str(e)}",
            "user_id": str(user_id),
            "email_type": "password_reset"
        }
