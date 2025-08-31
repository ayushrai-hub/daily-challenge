"""
Email sending tasks for the Daily Challenge application.

These tasks handle direct sending of emails (bypassing the queue) and 
enqueuing emails to be processed by the queue worker.
"""
import asyncio
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from typing import Dict, List, Optional, Union, Any
from uuid import UUID
from datetime import datetime

from app.services.email.email_service import EmailService
from app.services.email.queue_service import EmailQueueService
from app.services.email.templates import get_welcome_email_template, get_subscription_update_template, get_verification_email_template
from app.schemas.email import EmailCreate
from app.db.session import SessionLocal
from app.db.models.email_queue import EmailStatus
from app.core.config import settings

logger = get_logger()

@celery_app.task(name="app.tasks.email.send_email.send_direct_email", queue="emails")
async def send_direct_email(
    recipient: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
    force_send: bool = False
) -> Dict[str, Any]:
    """
    Send an email directly using the EmailService (bypassing the queue).
    
    Args:
        recipient: Email address of the recipient
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional)
        from_email: Sender email address (optional)
        force_send: Whether to send to emails that would normally be blocked
        
    Returns:
        Dictionary with status of the email sending operation
    """
    logger.info(f"Sending direct email to {recipient}: {subject}")
    
    try:
        result = await EmailService.send_email(
            to=recipient,
            subject=subject,
            html=html_content,
            text=text_content,
            from_email=from_email,
            force_send=force_send
        )
        logger.info(f"Email sent successfully to {recipient}")
        return {
            "success": True,
            "message": "Email sent successfully",
            "recipient": recipient,
            "subject": subject,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to send email: {str(e)}",
            "recipient": recipient,
            "subject": subject
        }

@celery_app.task(name="app.tasks.email.send_email.send_welcome_email", queue="emails")
def send_welcome_email(user_id: UUID, email: str, name: str) -> Dict[str, Any]:
    """
    Enqueue a welcome email to a newly registered user.
    
    Args:
        user_id: The user's ID
        email: The user's email address
        name: The user's full name
        
    Returns:
        Dictionary with status of the enqueue operation
    """
    logger.info(f"Enqueueing welcome email to {email} (User ID: {user_id})")
    
    try:
        # Generate the HTML content using the template
        html_content = get_welcome_email_template(user_name=name)
        
        # Create the email data
        email_data = EmailCreate(
            user_id=user_id,
            email_type="welcome",
            recipient=email,
            subject=f"Welcome to Daily Challenge, {name}!",
            html_content=html_content,
            text_content=f"Welcome to Daily Challenge, {name}!",
            template_id="welcome_email",
            template_data={"user_name": name}
        )
        
        # Enqueue the email
        with SessionLocal() as db:
            result = EmailQueueService.enqueue_email(db=db, email_data=email_data)
            
        logger.info(f"Welcome email enqueued for {email}, ID: {result.id}")
        return {
            "success": True,
            "message": f"Welcome email enqueued for {email}",
            "user_id": str(user_id),
            "email_id": str(result.id),
            "email_type": "welcome"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue welcome email for {email}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to enqueue welcome email: {str(e)}",
            "user_id": str(user_id),
            "email_type": "welcome"
        }


@celery_app.task(name="app.tasks.email.send_email.send_verification_email", queue="emails")
def send_verification_email(user_id: UUID, email: str, name: str, token: str) -> Dict[str, Any]:
    """
    Enqueue an email verification email to a user.
    
    Args:
        user_id: The user's ID
        email: The user's email address
        name: The user's full name
        token: The verification token
        
    Returns:
        Dictionary with status of the enqueue operation
    """
    logger.info(f"Enqueueing verification email to {email} (User ID: {user_id})")
    
    try:
        # Generate verification link
        verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        
        # Generate the HTML content using the template
        html_content = get_verification_email_template(
            user_name=name,
            verification_link=verification_link,
            token=token
        )
        
        # Create the email data
        email_data = EmailCreate(
            user_id=user_id,
            email_type="verification",
            recipient=email,
            subject=f"Please verify your email address - Daily Challenge",
            html_content=html_content,
            text_content=f"Please verify your email address for Daily Challenge. Verification link: {verification_link}",
            template_id="verification_email",
            template_data={
                "user_name": name,
                "verification_link": verification_link,
                "token": token
            }
        )
        
        # Enqueue the email
        with SessionLocal() as db:
            result = EmailQueueService.enqueue_email(db=db, email_data=email_data)
            
        logger.info(f"Verification email enqueued for {email}, ID: {result.id}")
        return {
            "success": True,
            "message": f"Verification email enqueued for {email}",
            "user_id": str(user_id),
            "email_id": str(result.id),
            "email_type": "verification"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue verification email for {email}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to enqueue verification email: {str(e)}",
            "user_id": str(user_id),
            "email_type": "verification"
        }

@celery_app.task(name="app.tasks.email.send_email.send_daily_challenge", queue="emails")
def send_daily_challenge(
    user_id: UUID, 
    email: str, 
    name: str,
    problem_id: UUID,
    problem_title: str,
    difficulty: str,
    problem_url: str,
    problem_description: str = None
) -> Dict[str, Any]:
    """
    Enqueue a daily challenge email to a subscribed user.
    
    Args:
        user_id: The user's ID
        email: The user's email address
        name: The user's name
        problem_id: The ID of the problem
        problem_title: The title of the problem
        difficulty: The difficulty level of the problem
        problem_url: URL to access the problem
        
    Returns:
        Dictionary with status of the enqueue operation
    """
    logger.info(f"Enqueueing daily challenge email to {email} (User ID: {user_id})")
    logger.info(f"Problem: {problem_title} (ID: {problem_id}, Difficulty: {difficulty})")
    
    try:
        # If problem_description is provided, use it, otherwise use a link-only template
        if problem_description:
            # Create HTML content with the full problem description
            html_content = f"""
            <h1>Your Daily Coding Challenge</h1>
            <p>Hello {name},</p>
            <p>Here's your daily coding challenge:</p>
            <div style="padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                <h2>{problem_title}</h2>
                <p><strong>Difficulty:</strong> {difficulty}</p>
                <div style="margin: 15px 0;">
                    <div>{problem_description}</div>
                </div>
                <a href="{problem_url}" style="display: inline-block; margin-top: 10px; padding: 10px 15px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;" target="_blank" rel="noopener noreferrer">View Online</a>
            </div>
            <p>The solution to this challenge will be sent to you in 24 hours.</p>
            <p>Happy coding!</p>
            <p>The Daily Challenge Team</p>
            """
        else:
            # Fallback to link-only template
            html_content = f"""
            <h1>Your Daily Coding Challenge</h1>
            <p>Hello {name},</p>
            <p>Here's your daily coding challenge:</p>
            <div style="padding: 15px; background-color: #f5f5f5; border-radius: 5px;">
                <h2>{problem_title}</h2>
                <p><strong>Difficulty:</strong> {difficulty}</p>
                <a href="{problem_url}" style="padding: 10px 15px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;" target="_blank" rel="noopener noreferrer">Solve Challenge</a>
            </div>
            <p>Happy coding!</p>
            <p>The Daily Challenge Team</p>
            """
        
        # Create the email data
        email_data = EmailCreate(
            user_id=user_id,
            email_type="daily_challenge",
            recipient=email,
            subject=f"Daily Challenge: {problem_title}",
            html_content=html_content,
            text_content=f"Your Daily Challenge: {problem_title} (Difficulty: {difficulty}). Solve it at: {problem_url}",
            template_id="daily_challenge",
            template_data={
                "user_name": name,
                "problem_title": problem_title,
                "problem_id": str(problem_id),
                "difficulty": difficulty,
                "problem_url": problem_url
            },
            # Add problem_id to create the link between email and delivery log
            problem_id=problem_id
        )
        
        # Enqueue the email
        with SessionLocal() as db:
            result = EmailQueueService.enqueue_email(db=db, email_data=email_data)
            
        logger.info(f"Daily challenge email enqueued for {email}, ID: {result.id}")
        return {
            "success": True,
            "message": f"Daily challenge email enqueued for {email}",
            "user_id": str(user_id),
            "problem_id": str(problem_id),
            "email_id": str(result.id),
            "email_type": "daily_challenge"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue daily challenge email for {email}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to enqueue daily challenge email: {str(e)}",
            "user_id": str(user_id),
            "problem_id": str(problem_id),
            "email_type": "daily_challenge"
        }

@celery_app.task(
    name="app.tasks.email.send_email.enqueue_batch_emails", 
    queue="emails",
    rate_limit="100/m",  # Limit to 100 emails per minute
    max_retries=3,       # Retry up to 3 times if it fails
    retry_backoff=True,  # Use exponential backoff for retries
)
def enqueue_batch_emails(
    email_type: str,
    user_data: List[Dict[str, Any]],
    subject_template: str,
    html_template: str,
    text_template: Optional[str] = None,
    template_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enqueue batch emails to multiple users.
    
    Args:
        email_type: Type of email to send (e.g., 'newsletter', 'reminder')
        user_data: List of user data dictionaries with ids, emails, and vars for templates
        subject_template: Template string for email subject with {var} placeholders
        html_template: HTML template string with {var} placeholders
        text_template: Plain text template string with {var} placeholders (optional)
        template_id: Template identifier for tracking purposes (optional)
        
    Returns:
        Dictionary with results of the batch enqueue operation
    """
    logger.info(f"Enqueueing batch {email_type} emails for {len(user_data)} users")
    
    success_count = 0
    failed_ids = []
    email_ids = []
    
    # Process each user
    for user in user_data:
        try:
            # Format the templates with user data
            try:
                subject = subject_template.format(**user)
                html_content = html_template.format(**user)
                text_content = text_template.format(**user) if text_template else None
            except KeyError as e:
                logger.error(f"Missing template variable in user data: {e}")
                failed_ids.append(user.get("id", "unknown"))
                continue
                
            # Create the email data
            email_data = EmailCreate(
                user_id=user["id"],
                email_type=email_type,
                recipient=user["email"],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_id=template_id or email_type,
                template_data=user
            )
            
            # Enqueue the email
            with SessionLocal() as db:
                result = EmailQueueService.enqueue_email(db=db, email_data=email_data)
                
            email_ids.append(str(result.id))
            success_count += 1
            logger.debug(f"Email enqueued for {user['email']}, ID: {result.id}")
        except Exception as e:
            logger.error(f"Failed to enqueue email for {user.get('email', 'unknown')}: {str(e)}")
            failed_ids.append(user.get("id", "unknown"))
    
    # Return statistics about the batch operation
    return {
        "success": (len(failed_ids) == 0),
        "email_type": email_type,
        "total_processed": len(user_data),
        "success_count": success_count,
        "failed_count": len(failed_ids),
        "failed_ids": failed_ids,
        "email_ids": email_ids,
        "timestamp": datetime.utcnow().isoformat()
    }
