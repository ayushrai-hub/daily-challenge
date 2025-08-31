"""
Daily Challenge Service

This module manages the scheduling and delivery of daily coding challenges
and their solutions to users, implementing:
1. Problem delivery scheduling
2. Solution delivery 24 hours after problem
3. Tracking of deliveries using DeliveryLog
4. Email queue management
"""
import asyncio
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.db.models.user import User
from app.db.models.problem import Problem, ProblemStatus
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus, DeliveryChannel
from app.db.models.email_queue import EmailQueue, EmailStatus
from app.services.daily_challenge.problem_selector import ProblemSelector
from app.services.email.email_service import EmailService
from app.services.email.templates import get_daily_challenge_email_template, get_challenge_solution_email_template
from app.tasks.email.send_email import send_daily_challenge
from app.tasks.email.send_solution_email import send_challenge_solution
from app.core.logging import get_logger

logger = get_logger()

class DailyChallengeService:
    """
    Service for scheduling and delivering daily coding challenges and solutions.
    Handles the complete lifecycle of challenge delivery including problem selection,
    email scheduling, and delivery tracking.
    """
    
    # Default hour to deliver challenges (8:00 AM UTC)
    DEFAULT_DELIVERY_HOUR = 8
    
    # Hours to wait before sending solution (24 hours)
    SOLUTION_DELAY_HOURS = 24
    
    @classmethod
    async def schedule_daily_challenges(
        cls, 
        db: Session,
        delivery_hour: int = DEFAULT_DELIVERY_HOUR
    ) -> Dict[str, Any]:
        """
        Schedule daily coding challenges for all eligible users.
        
        Args:
            db: Database session
            delivery_hour: Hour of day to deliver challenges (0-23)
            
        Returns:
            Dictionary with results summary
        """
        logger.info(f"Starting daily challenge scheduling (delivery hour: {delivery_hour})")
        
        # Get all active, verified users
        eligible_users = (
            db.query(User)
            .filter(
                User.is_active == True,
                User.is_email_verified == True
            )
            .all()
        )
        
        logger.info(f"Found {len(eligible_users)} eligible users for daily challenges")
        
        results = {
            "total_users": len(eligible_users),
            "scheduled": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        # Calculate delivery time (today at the specified hour)
        today = datetime.utcnow().replace(
            hour=delivery_hour, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        # Process each eligible user
        for user in eligible_users:
            try:
                # Select a problem for the user
                problem = await ProblemSelector.select_problem_for_user(db, user.id)
                
                if not problem:
                    logger.warning(f"No suitable problem found for user {user.id}")
                    results["skipped"] += 1
                    results["details"].append({
                        "user_id": str(user.id),
                        "status": "skipped",
                        "reason": "no_suitable_problem"
                    })
                    continue
                
                # Idempotency check: skip if already scheduled, pending, or delivered
                existing_log = (
                    db.query(DeliveryLog)
                    .filter(
                        DeliveryLog.user_id == user.id,
                        DeliveryLog.problem_id == problem.id,
                        DeliveryLog.status.in_([
                            DeliveryStatus.scheduled,
                            DeliveryStatus.failed,
                            DeliveryStatus.delivered
                        ])
                    )
                    .first()
                )
                if existing_log:
                    logger.info(f"[Idempotency] Problem email already scheduled/sent for user {user.id} and problem {problem.id}")
                    results["skipped"] += 1
                    results["details"].append({
                        "user_id": str(user.id),
                        "problem_id": str(problem.id),
                        "status": "skipped",
                        "reason": "problem_already_scheduled_or_sent"
                    })
                    continue
                # Otherwise, create new delivery log entry
                    # Create new delivery log entry
                    delivery_log = DeliveryLog(
                        user_id=user.id,
                        problem_id=problem.id,
                        status=DeliveryStatus.scheduled,
                        delivery_channel=DeliveryChannel.email,
                        scheduled_at=today
                    )
                    db.add(delivery_log)
                
                # Use the existing task to queue the problem email
                # Get the difficulty level (string value from enum)
                difficulty = problem.difficulty_level.value if problem.difficulty_level else "medium"
                
                # Construct proper URL with frontend URL from settings
                from app.core.config import settings
                frontend_url = settings.FRONTEND_URL.rstrip('/')
                problem_url = f"{frontend_url}/problem/{problem.id}"  # Note: Using /problem/ (singular) not /problems/
                
                task_result = send_daily_challenge.delay(
                    user_id=user.id,
                    email=user.email,
                    name=user.full_name or user.email.split('@')[0],
                    problem_id=problem.id,
                    problem_title=problem.title,
                    difficulty=difficulty,
                    problem_url=problem_url,
                    problem_description=problem.description
                )
                
                # Store the task ID in the delivery log metadata
                delivery_log.meta = {
                    "celery_task_id": str(task_result.id)
                }
                
                # Update user's last problem tracking
                user.last_problem_sent_id = problem.id
                user.last_problem_sent_at = today
                
                # We'll schedule the solution email in the separate solution scheduler task 
                # that runs periodically - this way we ensure it's only sent after 
                # the problem is confirmed delivered
                
                results["scheduled"] += 1
                results["details"].append({
                    "user_id": str(user.id),
                    "problem_id": str(problem.id),
                    "status": "scheduled",
                    "delivery_time": today.isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error scheduling challenge for user {user.id}: {str(e)}")
                results["errors"] += 1
                results["details"].append({
                    "user_id": str(user.id),
                    "status": "error",
                    "error": str(e)
                })
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Daily challenge scheduling completed: {results['scheduled']} scheduled, "
                   f"{results['skipped']} skipped, {results['errors']} errors")
        
        return results
    
    @classmethod
    async def _schedule_solution_email(
        cls,
        db: Session,
        user: User,
        problem: Problem,
        delivery_time: datetime
    ) -> Optional[Any]:
        """
        Schedule a solution email to be sent later using the task system.
        
        Args:
            db: Database session
            user: User to send solution to
            problem: Problem with solution
            delivery_time: When to deliver the solution
            
        Returns:
            Task result object if scheduled successfully, None otherwise
        """
        if not problem.solution:
            logger.warning(f"Cannot schedule solution email for problem {problem.id}: No solution available")
            return {
                "success": False,
                "message": f"Cannot schedule solution email for problem {problem.id}: No solution available",
                "problem_id": str(problem.id),
                "user_id": str(user.id)
            }
        
        try:
            # Use the existing task to send the solution email
            # If delivery_time is in the future, the EmailQueue will handle the scheduling
            task_result = send_challenge_solution.apply_async(
                kwargs={
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.full_name or user.email.split('@')[0],
                    "problem_id": str(problem.id),
                    "problem_title": problem.title,
                    "problem_description": problem.description,
                    "problem_solution": problem.solution
                },
                eta=delivery_time  # Schedule for future delivery
            )
            
            logger.info(f"Scheduled solution email for user {user.id}, problem {problem.id} "
                        f"at {delivery_time.isoformat()} with task ID: {task_result.id}")
            return {
                "success": True,
                "message": f"Solution email scheduled for user {user.id}, problem {problem.id}",
                "task_id": str(task_result.id),
                "user_id": str(user.id),
                "problem_id": str(problem.id)
            }
            
        except Exception as e:
            logger.error(f"Error scheduling solution email for user {user.id}, problem {problem.id}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to schedule solution email: {str(e)}",
                "user_id": str(user.id),
                "problem_id": str(problem.id)
            }
    
    # These methods are no longer needed - we're using the standardized templates
    # from app.services.email.templates
    
    # This method is removed - we're using the standardized templates
    
    @classmethod
    async def schedule_pending_solutions(cls, db: Session) -> Dict[str, Any]:
        """
        Schedule solution emails for problems that were delivered ~24 hours ago.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with results summary
        """
        logger.info("Starting pending solution scheduling")
        
        # Calculate time window for problems delivered after the delay period
        now = datetime.utcnow()
        target_time = now - timedelta(hours=cls.SOLUTION_DELAY_HOURS)
        
        # Calculate time window for problems delivered ~24 hours ago
        # Use a window that's proportional to the delay (5% of delay time on each side)
        # For 24 hours, this gives a ~2.4 hour window (±1.2 hours around target time)
        window_margin = timedelta(hours=cls.SOLUTION_DELAY_HOURS * 0.05)
        
        # Ensure window is at least 30 minutes and at most 3 hours
        window_margin = max(timedelta(minutes=30), min(window_margin, timedelta(hours=3)))
        
        window_start = target_time - window_margin
        window_end = target_time + window_margin
        
        logger.info(f"SOLUTION_DELAY_HOURS: {cls.SOLUTION_DELAY_HOURS}")
        logger.info(f"Current time: {now.isoformat()}")
        logger.info(f"Target time: {target_time.isoformat()}")
        logger.info(f"Window start: {window_start.isoformat()}")
        logger.info(f"Window end: {window_end.isoformat()}")
        
        # Find delivery logs for problems delivered in the target time window
        # Using more reliable approach to filter based on JSON fields
        from sqlalchemy import or_, func, text
        
        # Debug log the time window
        logger.info(f"Looking for delivery logs between {window_start.isoformat()} and {window_end.isoformat()}")
        
        # First, get all logs in the time window
        delivery_logs = (
            db.query(DeliveryLog)
            .filter(
                DeliveryLog.status == DeliveryStatus.delivered,
                DeliveryLog.delivered_at >= window_start,
                DeliveryLog.delivered_at <= window_end
            )
            .all()
        )
        
        logger.info(f"Found {len(delivery_logs)} delivery logs in the time window")
        
        # Then filter them in Python to handle the JSON fields properly
        eligible_logs = []
        for log in delivery_logs:
            # Initialize meta if it doesn't exist
            meta = log.meta or {}
            
            # Check if solution has already been scheduled or delivered
            if 'solution_scheduled_at' not in meta and 'solution_delivered_at' not in meta:
                eligible_logs.append(log)
            else:
                logger.debug(f"Skipping log {log.id}: Solution already scheduled or delivered")
        
        logger.info(f"After JSON filtering, found {len(eligible_logs)} eligible logs for solution emails")
        
        logger.info(f"Found {len(eligible_logs)} delivery logs eligible for solution emails")
        
        results = {
            "total": len(eligible_logs),
            "scheduled": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        # Process each eligible delivery log
        for log in eligible_logs:
            try:
                # Check idempotency: skip if solution already scheduled or delivered
                meta = log.meta or {}
                if "solution_scheduled_at" in meta or "solution_delivered_at" in meta:
                    logger.info(f"[Idempotency] Solution email already scheduled/sent for user {log.user_id} and problem {log.problem_id}")
                    results["skipped"] += 1
                    results["details"].append({
                        "user_id": str(log.user_id),
                        "problem_id": str(log.problem_id),
                        "status": "skipped",
                        "reason": "solution_already_scheduled_or_sent"
                    })
                    continue
                # Fetch the user and problem
                user = db.query(User).filter(User.id == log.user_id).first()
                problem = db.query(Problem).filter(Problem.id == log.problem_id).first()
                
                if not user or not user.is_active or not user.is_email_verified:
                    logger.warning(f"Skipping solution for user {log.user_id}: User not found or inactive")
                    results["skipped"] += 1
                    results["details"].append({
                        "user_id": str(log.user_id),
                        "problem_id": str(log.problem_id),
                        "status": "skipped",
                        "reason": "user_not_eligible"
                    })
                    continue
                
                if not problem or not problem.solution:
                    logger.warning(f"Skipping solution for problem {log.problem_id}: Problem not found or no solution")
                    results["skipped"] += 1
                    results["details"].append({
                        "user_id": str(log.user_id),
                        "problem_id": str(log.problem_id),
                        "status": "skipped",
                        "reason": "problem_not_eligible"
                    })
                    continue
                
                # Schedule the solution email to be sent immediately
                solution_email = await cls._schedule_solution_email(
                    db,
                    user,
                    problem,
                    now  # Send immediately since it's already been 24 hours
                )
                
                if solution_email:
                    # Update the delivery log to mark solution as scheduled
                    meta = log.meta or {}
                    meta["solution_scheduled_at"] = now.isoformat()
                    meta["solution_email_id"] = str(solution_email.id) if hasattr(solution_email, 'id') else str(solution_email)
                    log.meta = meta
                    
                    results["scheduled"] += 1
                    results["details"].append({
                        "user_id": str(log.user_id),
                        "problem_id": str(log.problem_id),
                        "status": "scheduled",
                        "email_id": str(solution_email.id) if hasattr(solution_email, 'id') else str(solution_email)
                    })
                else:
                    results["errors"] += 1
                    results["details"].append({
                        "user_id": str(log.user_id),
                        "problem_id": str(log.problem_id),
                        "status": "error",
                        "reason": "email_scheduling_failed"
                    })
            
            except Exception as e:
                logger.error(f"Error scheduling solution email for log {log.id}: {str(e)}")
                results["errors"] += 1
                results["details"].append({
                    "log_id": str(log.id),
                    "status": "error",
                    "error": str(e)
                })
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Solution scheduling completed: {results['scheduled']} scheduled, "
                   f"{results['skipped']} skipped, {results['errors']} errors")
        
        return results

    @classmethod
    async def process_email_queue(cls, db: Session) -> Dict[str, Any]:
        """
        Process the email queue and send out scheduled emails.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with processing results
        """
        now = datetime.utcnow()
        logger.info(f"Processing email queue at {now.isoformat()}")
        
        # Find emails scheduled for now or earlier
        pending_emails = (
            db.query(EmailQueue)
            .filter(
                EmailQueue.status == EmailStatus.pending,
                EmailQueue.scheduled_for <= now
            )
            .all()
        )
        
        logger.info(f"Found {len(pending_emails)} pending emails to process")
        
        results = {
            "total": len(pending_emails),
            "sent": 0,
            "failed": 0,
            "details": []
        }
        
        for email in pending_emails:
            try:
                # Send the email
                response = await EmailService.send_email(
                    to=email.recipient,
                    subject=email.subject,
                    html=email.html_content,
                    force_send=True  # Ensure it's sent even in test environments
                )
                
                # Update email status
                email.status = EmailStatus.sent
                email.sent_at = now
                email.delivery_data = response
                
                # Update delivery log if this is a challenge email
                if email.problem_id:
                    delivery_log = (
                        db.query(DeliveryLog)
                        .filter(
                            DeliveryLog.user_id == email.user_id,
                            DeliveryLog.problem_id == email.problem_id
                        )
                        .order_by(DeliveryLog.created_at.desc())
                        .first()
                    )
                    
                    if delivery_log:
                        delivery_log.status = DeliveryStatus.delivered
                        delivery_log.delivered_at = now
                        
                        # If this was a solution email, add to meta
                        if email.email_type == "daily_challenge_solution":
                            meta = delivery_log.meta or {}
                            meta["solution_delivered_at"] = now.isoformat()
                            meta["solution_email_id"] = str(email.id)
                            delivery_log.meta = meta
                
                results["sent"] += 1
                results["details"].append({
                    "email_id": str(email.id),
                    "recipient": email.recipient,
                    "subject": email.subject,
                    "status": "sent"
                })
                
            except Exception as e:
                logger.error(f"Error sending email {email.id}: {str(e)}")
                
                # Update email status
                email.status = EmailStatus.failed
                email.error_message = str(e)
                
                results["failed"] += 1
                results["details"].append({
                    "email_id": str(email.id),
                    "recipient": email.recipient,
                    "subject": email.subject,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Email queue processing completed: {results['sent']} sent, {results['failed']} failed")
        
        return results
