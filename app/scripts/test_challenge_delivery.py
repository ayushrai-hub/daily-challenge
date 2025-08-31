#!/usr/bin/env python
"""
Test script for challenge and solution delivery.
Sends a test problem to a specific user and sets up for solution delivery.
"""
import asyncio
import sys
import uuid
from datetime import datetime
from sqlalchemy import func

# Add the project root to sys.path
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.db.models.user import User
from app.db.models.problem import Problem
from app.tasks.email.send_email import send_daily_challenge
from app.db.models.delivery_log import DeliveryLog, DeliveryStatus, DeliveryChannel
from app.core.logging import get_logger

logger = get_logger()

async def send_test_challenge():
    """Send a test challenge to a specific user for testing solution delivery."""
    user_email = "aayushjain1475@gmail.com"
    
    with SessionLocal() as db:
        # Get user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            logger.error(f"User {user_email} not found")
            return

        # Find a problem with a solution that hasn't been sent to this user yet
        existing_problem_ids = [
            log.problem_id for log in db.query(DeliveryLog.problem_id)
            .filter(DeliveryLog.user_id == user.id)
            .all()
        ]
        
        problem = db.query(Problem)\
            .filter(Problem.solution.isnot(None))\
            .filter(~Problem.id.in_(existing_problem_ids) if existing_problem_ids else True)\
            .order_by(func.random())\
            .first()
            
        if not problem:
            logger.error(f"No available problems with solutions found for {user_email}")
            return
            
        logger.info(f"Sending test challenge to {user.email} (ID: {user.id})")
        logger.info(f"Problem: {problem.title} (ID: {problem.id})")
        
        # Create delivery log
        delivery_log = DeliveryLog(
            user_id=user.id,
            problem_id=problem.id,
            status=DeliveryStatus.scheduled,
            delivery_channel=DeliveryChannel.email,
            scheduled_at=datetime.utcnow(),
            meta={"test_delivery": True}
        )
        db.add(delivery_log)
        db.commit()
        
        # Send the challenge email using the Celery task
        result = send_daily_challenge(
            user_id=user.id, 
            email=user.email,
            name=user.full_name or user.email.split('@')[0],
            problem_id=problem.id,
            problem_title=problem.title,
            difficulty=str(problem.difficulty_level),
            problem_url=f"http://localhost/problem/{problem.id}",
            problem_description=problem.description
        )
        
        logger.info(f"Challenge email result: {result}")
        logger.info("Check for solution email in ~5 minutes (modified delay for testing)")
        
        return result

if __name__ == "__main__":
    result = asyncio.run(send_test_challenge())
    print(f"Result: {result}")
    print("Check logs and email queue tables to verify problem email was sent correctly.")
    print("Then verify solution email is sent approximately 5 minutes later.")
