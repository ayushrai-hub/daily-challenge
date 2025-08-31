"""
Solution email sending tasks for the Daily Challenge application.

These tasks handle the sending of solution emails 24 hours after the problem was delivered.
"""
import asyncio
from app.core.celery_app import celery_app
from app.core.logging import get_logger
from typing import Dict, Any
from uuid import UUID
from datetime import datetime

from app.services.email.email_service import EmailService
from app.services.email.queue_service import EmailQueueService
from app.services.email.templates import get_challenge_solution_email_template
from app.schemas.email import EmailCreate
from app.db.session import SessionLocal
from app.db.models.problem import Problem
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus

logger = get_logger()


@celery_app.task(name="app.tasks.email.send_solution_email.send_challenge_solution", queue="emails")
def send_challenge_solution(
    user_id: UUID, 
    email: str, 
    name: str,
    problem_id: UUID,
    problem_title: str,
    problem_description: str,
    problem_solution: str
) -> Dict[str, Any]:
    """
    Enqueue a solution email for a previously sent daily challenge.
    
    Args:
        user_id: The user's ID
        email: The user's email address
        name: The user's name
        problem_id: The ID of the problem
        problem_title: The title of the problem
        problem_description: The problem description/statement
        problem_solution: The solution to the problem
        
    Returns:
        Dictionary with status of the enqueue operation
    """
    logger.info(f"Enqueueing solution email to {email} (User ID: {user_id})")
    logger.info(f"Problem solution: {problem_title} (ID: {problem_id})")
    
    try:
        # Use the solution email template
        html_content = get_challenge_solution_email_template(
            user_name=name,
            problem=problem_description,
            solution=problem_solution,
            problem_title=problem_title
        )
        
        # Create the email data
        email_data = EmailCreate(
            user_id=user_id,
            email_type="daily_challenge_solution",
            recipient=email,
            subject=f"Solution: {problem_title}",
            html_content=html_content,
            text_content=f"Solution for yesterday's challenge: {problem_title}",
            template_id="daily_challenge_solution",
            template_data={
                "user_name": name,
                "problem_title": problem_title,
                "problem_id": str(problem_id),
                "is_solution": True
            },
            problem_id=problem_id
        )
        
        # Enqueue the email
        with SessionLocal() as db:
            result = EmailQueueService.enqueue_email(db=db, email_data=email_data)
            
            # Update delivery log if it exists
            delivery_log = (
                db.query(DeliveryLog)
                .filter(
                    DeliveryLog.user_id == user_id,
                    DeliveryLog.problem_id == problem_id,
                    DeliveryLog.status == DeliveryStatus.delivered
                )
                .order_by(DeliveryLog.created_at.desc())
                .first()
            )
            
            if delivery_log:
                # Add solution delivery information to meta
                meta = delivery_log.meta or {}
                meta["solution_scheduled_at"] = datetime.utcnow().isoformat()
                meta["solution_email_id"] = str(result.id)
                delivery_log.meta = meta
                db.commit()
            
        logger.info(f"Solution email enqueued for {email}, ID: {result.id}")
        return {
            "success": True,
            "message": f"Solution email enqueued for {email}",
            "user_id": str(user_id),
            "problem_id": str(problem_id),
            "email_id": str(result.id),
            "email_type": "daily_challenge_solution"
        }
    except Exception as e:
        logger.error(f"Failed to enqueue solution email for {email}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to enqueue solution email: {str(e)}",
            "user_id": str(user_id),
            "problem_id": str(problem_id),
            "email_type": "daily_challenge_solution"
        }
