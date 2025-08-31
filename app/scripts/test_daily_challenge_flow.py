"""
Test script to manually trigger the daily challenge flow.

This script allows testing of:
1. Daily problem scheduling
2. Solution email scheduling
3. Simulating webhook events
4. Verifying delivery logs
"""
import asyncio
import sys
import os
import httpx
from datetime import datetime, timedelta
import pytz
import json
from uuid import UUID

from sqlalchemy import update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db, async_session

# Add the parent directory to the Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.core.logging import setup_logging, get_logger
from app.services.daily_challenge.challenge_service import DailyChallengeService
from app.db.models.user import User
from app.db.models.problem import Problem
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus

# Set up logging
setup_logging()
logger = get_logger()

async def test_schedule_problems():
    """Test scheduling daily problems for all eligible users."""
    logger.info("Testing daily problem scheduling...")
    
    with SessionLocal() as db:
        # Count eligible users before scheduling
        eligible_users = (
            db.query(User)
            .filter(
                User.is_active == True,
                User.is_email_verified == True
            )
            .count()
        )
        
        logger.info(f"Found {eligible_users} eligible users for daily challenges")
        
        # Schedule problems (current hour for immediate delivery)
        current_hour = datetime.utcnow().hour
        results = await DailyChallengeService.schedule_daily_challenges(db, current_hour)
        
        logger.info(f"Daily challenge scheduling results: {results['scheduled']} scheduled, "
                  f"{results['skipped']} skipped, {results['errors']} errors")
        
        return results

async def test_schedule_solutions():
    """Test scheduling solution emails for problems delivered recently."""
    logger.info("Testing solution email scheduling...")
    
    with SessionLocal() as db:
        # Get all delivery logs to check what's available
        delivery_logs = db.query(DeliveryLog).filter(
            DeliveryLog.status == DeliveryStatus.delivered
        ).limit(10).all()
        
        if not delivery_logs:
            logger.warning("No delivered problems found. Need to deliver problems first.")
            return {"scheduled": 0, "skipped": 0, "errors": 0, "details": []}
        
        logger.info(f"Found {len(delivery_logs)} delivered problems")
        
        # Schedule solutions
        results = await DailyChallengeService.schedule_pending_solutions(db)
        
        logger.info(f"Solution scheduling results: {results['scheduled']} scheduled, "
                  f"{results['skipped']} skipped, {results['errors']} errors")
        
        return results

async def force_schedule_all_solutions():
    """Force scheduling of solution emails for all delivered problems regardless of time."""
    logger.info("Forcing solution emails for all delivered problems...")
    
    # This is only for testing - normally we'd respect the 24-hour delay
    with SessionLocal() as db:
        from sqlalchemy.dialects.postgresql import JSONB
        # Use proper SQLAlchemy JSONB operators
        delivery_logs = db.query(DeliveryLog).filter(
            DeliveryLog.status.in_([DeliveryStatus.delivered, DeliveryStatus.completed]),
            DeliveryLog.meta.is_(None) | ~DeliveryLog.meta.cast(JSONB).has_key('solution_delivered_at'),
            DeliveryLog.meta.is_(None) | ~DeliveryLog.meta.cast(JSONB).has_key('solution_scheduled_at')
        ).all()
        
        logger.info(f"Found {len(delivery_logs)} problems eligible for solution emails")
        
        scheduled = 0
        skipped = 0
        errors = 0
        
        for log in delivery_logs:
            user = db.query(User).filter(User.id == log.user_id).first()
            problem = db.query(Problem).filter(Problem.id == log.problem_id).first()
            
            if not user or not problem or not problem.solution:
                logger.warning(f"Skipping solution for log {log.id}: Missing user or problem data")
                skipped += 1
                continue
            
            # Schedule for immediate delivery
            now = datetime.utcnow()
            result = await DailyChallengeService._schedule_solution_email(db, user, problem, now)
            
            if result:
                # Update the delivery log
                meta = log.meta or {}
                meta["solution_scheduled_at"] = now.isoformat()
                log.meta = meta
                scheduled += 1
                logger.info(f"Scheduled solution for user {user.id}, problem {problem.id}")
            else:
                errors += 1
                logger.error(f"Failed to schedule solution for log {log.id}")
        
        db.commit()
        
        return {
            "scheduled": scheduled,
            "skipped": skipped,
            "errors": errors
        }

async def process_email_queue():
    """Process the email queue to send pending emails."""
    logger.info("Processing email queue...")
    
    with SessionLocal() as db:
        results = await DailyChallengeService.process_email_queue(db)
        
        logger.info(f"Email queue processing results: {results['sent']} sent, "
                  f"{results['failed']} failed")
        
        return results

async def test_process_email_queue():
    """Test email queue processing."""
    logger.info("Processing email queue...")
    
    with SessionLocal() as db:
        # Use the DailyChallengeService.process_email_queue method which we know works
        results = await DailyChallengeService.process_email_queue(db)
        
        logger.info(f"Email queue processing results: {results['sent']} sent, "
                  f"{results['failed']} failed")
        
        return results

async def simulate_webhook_events(webhook_url = None):
    """Simulate Resend webhook events to update delivery logs."""
    logger.info("=== SIMULATING WEBHOOK EVENTS ===")
    
    if not webhook_url:
        # Default to localhost if no URL provided
        webhook_url = "http://localhost:8000/api/webhooks/resend"
    
    webhook_events_sent = 0
    webhook_events_failed = 0
    
    async with async_session() as db:
        # Get all scheduled delivery logs
        from app.db.models.delivery_log import DeliveryLog, DeliveryStatus
        from app.db.models.user import User
        from app.db.models.problem import Problem
        
        # Find all scheduled delivery logs
        result = await db.execute(
            select(DeliveryLog, User, Problem)
            .join(User, DeliveryLog.user_id == User.id)
            .join(Problem, DeliveryLog.problem_id == Problem.id)
            .filter(DeliveryLog.status == DeliveryStatus.scheduled)
        )
        
        delivery_items = result.all()
        logger.info(f"Found {len(delivery_items)} scheduled delivery logs to simulate")
        
        for delivery_log, user, problem in delivery_items:
            # First simulate delivered event
            delivered_payload = {
                "type": "email.delivered",
                "data": {
                    "email_id": str(UUID(int=0)),  # Dummy ID
                    "to": user.email,
                    "subject": f"Daily Challenge: {problem.title}",
                    "from": "Daily Challenge <hello@info.focdot.com>"
                }
            }
            
            try:
                # Call the webhook endpoint using httpx (async-compatible)
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url,
                        json=delivered_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=5.0
                    )
                
                if response.status_code == 200:
                    logger.info(f"Simulated delivered event for {user.email} - {problem.title}")
                    webhook_events_sent += 1
                else:
                    logger.warning(f"Failed to simulate delivered event: {response.status_code} - {response.text}")
                    webhook_events_failed += 1
                    
                # Short delay to avoid overwhelming the server
                await asyncio.sleep(0.2)
                
                # Next simulate opened event
                opened_payload = {
                    "type": "email.opened",
                    "data": {
                        "email_id": str(UUID(int=0)),  # Dummy ID
                        "to": user.email,
                        "subject": f"Daily Challenge: {problem.title}",
                        "from": "Daily Challenge <hello@info.focdot.com>"
                    }
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url,
                        json=opened_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=5.0
                    )
                
                if response.status_code == 200:
                    logger.info(f"Simulated opened event for {user.email} - {problem.title}")
                    webhook_events_sent += 1
                else:
                    logger.warning(f"Failed to simulate opened event: {response.status_code} - {response.text}")
                    webhook_events_failed += 1
                    
                # Short delay
                await asyncio.sleep(0.2)
                
                # Finally simulate clicked event
                from app.core.config import settings
                frontend_url = settings.FRONTEND_URL.rstrip('/')
                clicked_payload = {
                    "type": "email.clicked",
                    "data": {
                        "email_id": str(UUID(int=0)),  # Dummy ID
                        "to": user.email,
                        "subject": f"Daily Challenge: {problem.title}",
                        "from": "Daily Challenge <hello@info.focdot.com>",
                        "url": f"{frontend_url}/problem/{problem.id}"
                    }
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url,
                        json=clicked_payload,
                        headers={"Content-Type": "application/json"},
                        timeout=5.0
                    )
                
                if response.status_code == 200:
                    logger.info(f"Simulated clicked event for {user.email} - {problem.title}")
                    webhook_events_sent += 1
                else:
                    logger.warning(f"Failed to simulate clicked event: {response.status_code} - {response.text}")
                    webhook_events_failed += 1
                    
            except Exception as e:
                logger.error(f"Error simulating webhook events: {str(e)}")
                webhook_events_failed += 1
                
            # Short delay between users
            await asyncio.sleep(0.2)
            
    return {
        "sent": webhook_events_sent,
        "failed": webhook_events_failed
    }

async def verify_delivery_logs():
    """Verify that delivery logs were properly updated by webhooks."""
    logger.info("=== VERIFYING DELIVERY LOGS ===")
    
    async with async_session() as db:
        from app.db.models.delivery_log import DeliveryLog, DeliveryStatus
        
        # Count logs by status
        result = await db.execute(
            select(DeliveryLog.status, func.count(DeliveryLog.id))
            .group_by(DeliveryLog.status)
        )
        
        status_counts = {status: count for status, count in result.all()}
        
        # Count logs with opened_at set
        result = await db.execute(
            select(func.count(DeliveryLog.id))
            .filter(DeliveryLog.opened_at != None)
        )
        opened_count = result.scalar_one()
        
        # Count logs with completed_at set
        result = await db.execute(
            select(func.count(DeliveryLog.id))
            .filter(DeliveryLog.completed_at != None)
        )
        completed_count = result.scalar_one()
        
        return {
            "status_counts": status_counts,
            "opened_count": opened_count,
            "completed_count": completed_count
        }

async def main():
    """Main test function to run the complete flow."""
    action = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if action in ["all", "problems"]:
        logger.info("=== TESTING PROBLEM SCHEDULING ===")
        problem_results = await test_schedule_problems()
        print(f"\nProblem Scheduling Results:")
        print(f"- Scheduled: {problem_results['scheduled']}")
        print(f"- Skipped: {problem_results['skipped']}")
        print(f"- Errors: {problem_results['errors']}")
    
    if action in ["all", "webhooks"]:
        # Simulate webhook events to update delivery logs
        webhook_results = await simulate_webhook_events()
        print(f"\nWebhook Simulation Results:")
        print(f"- Events Sent: {webhook_results['sent']}")
        print(f"- Events Failed: {webhook_results['failed']}")
        
        # Verify delivery logs were updated
        verification = await verify_delivery_logs()
        print(f"\nDelivery Log Verification:")
        print(f"- Status Counts: {verification['status_counts']}")
        print(f"- Opened Count: {verification['opened_count']}")
        print(f"- Completed Count: {verification['completed_count']}")
    
    if action in ["all", "solutions"]:
        logger.info("=== TESTING SOLUTION SCHEDULING ===")
        solution_results = await test_schedule_solutions()
        print(f"\nSolution Scheduling Results:")
        print(f"- Scheduled: {solution_results['scheduled']}")
        print(f"- Skipped: {solution_results['skipped']}")
        print(f"- Errors: {solution_results['errors']}")
    
    if action in ["all", "emails"]:
        logger.info("=== PROCESSING EMAIL QUEUE ===")
        email_results = await test_process_email_queue()
        print(f"\nEmail Processing Results:")
        print(f"- Sent: {email_results['sent']}")
        print(f"- Failed: {email_results['failed']}")
    
    if action in ["force-solutions"]:
        logger.info("=== FORCING SOLUTION SCHEDULING ===")
        force_results = await force_schedule_all_solutions()
        print(f"\nForced Solution Results:")
        print(f"- Scheduled: {force_results['scheduled']}")
        print(f"- Skipped: {force_results['skipped']}")
        print(f"- Errors: {force_results['errors']}")
        
    if action == "verify":
        # Just verify current delivery logs
        verification = await verify_delivery_logs()
        print(f"\nDelivery Log Status:")
        print(f"- Status Counts: {verification['status_counts']}")
        print(f"- Opened Count: {verification['opened_count']}")
        print(f"- Completed Count: {verification['completed_count']}")
        
    if action in ["all", "process"]:
        logger.info("=== PROCESSING EMAIL QUEUE ===")
        process_results = await process_email_queue()
        print(f"\nEmail Processing Results:")
        print(f"- Sent: {process_results['sent']}")
        print(f"- Failed: {process_results['failed']}")

if __name__ == "__main__":
    asyncio.run(main())
