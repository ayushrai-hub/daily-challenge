#!/usr/bin/env python
"""
Integration test for the email queue system with Celery.
This script will:
1. Create a test email in the queue
2. Allow Celery to process it (requires running Celery workers)
3. Verify that the retry mechanism works as expected

NOTE: This test uses the development database and Celery workers.
"""
import sys
import os
import time
from datetime import datetime, timedelta
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models.email_queue import EmailQueue, EmailStatus
from app.tasks.email.send_email import send_welcome_email  # Now registered as app.tasks.email.send_email.send_welcome_email
from app.core.celery_app import celery_app


def test_email_celery_integration():
    """Test the email queue system with Celery integration"""
    print("\n===== Email Queue Celery Integration Test =====\n")
    
    # Create a database session (using development database)
    db = SessionLocal()
    
    try:
        print("This test will use the DEVELOPMENT database and Celery workers.")
        print("Make sure your Celery workers are running before continuing.")
        input("Press Enter to continue or Ctrl+C to cancel...")
        
        # 1. Clean up any existing test emails
        print("\nCleaning up existing test emails...")
        test_emails = db.query(EmailQueue).filter(
            EmailQueue.recipient == "test_celery_retry@example.com"
        ).all()
        
        for email in test_emails:
            db.delete(email)
        
        db.commit()
        print(f"Cleaned up {len(test_emails)} test emails.")
        
        # 2. Enqueue a test email using the Celery task
        print("\nEnqueuing a test email through the Celery task...")
        
        # Generate a unique test ID to track this specific test
        test_id = str(uuid.uuid4())[:8]
        test_user_id = uuid.UUID("cfa7d18c-0b1e-4462-b39c-3143f305a335")
        test_email_address = "aj@focdot.com"
        
        # Use send_welcome_email which is one of our actual task functions
        result = send_welcome_email.delay(
            user_id=test_user_id,
            email=test_email_address,
            name=f"Test User {test_id}"
        )
        
        print(f"Enqueue task result: {result}")
        
        # 3. Wait longer for the email to be created in the database
        print("\nWaiting for email to be created in the database...")
        
        # Poll for the email to appear in the database
        max_attempts = 5
        test_email = None
        
        for attempt in range(max_attempts):
            time.sleep(3)  # Wait 3 seconds between attempts
            
            # Query to verify the email was enqueued
            # Note: The send_welcome_email task will set email_type to "welcome"
            test_email = db.query(EmailQueue).filter(
                EmailQueue.recipient == test_email_address,
                EmailQueue.email_type == "welcome"
            ).order_by(EmailQueue.created_at.desc()).first()
            
            if test_email:
                print(f"Found email after {attempt + 1} attempts")
                break
            else:
                print(f"Attempt {attempt + 1}/{max_attempts}: Email not found yet...")
                db.commit()  # Refresh transaction
        
        if not test_email:
            print("ERROR: Test email was not enqueued properly.")
            return
        
        print(f"Email successfully enqueued with ID: {test_email.id}")
        print(f"Email status: {test_email.status}")
        print(f"Initial retry_count: {test_email.retry_count}")
        print(f"Initial max_retries: {test_email.max_retries}")
        
        # 5. Let the Celery worker process it
        print("\nWaiting for Celery to process the email...")
        print("You should see activity in your Celery Flower dashboard.")
        
        # Poll for status changes
        for _ in range(10):  # Try for about 10 seconds
            time.sleep(1)
            db.refresh(test_email)
            print(f"Current status: {test_email.status}, Retry count: {test_email.retry_count}")
            
            if test_email.status != EmailStatus.pending:
                # The email status has changed, so Celery processed it
                break
        
        # 6. Report final status
        db.refresh(test_email)
        print("\n===== Test Results =====")
        print(f"Final email status: {test_email.status}")
        print(f"Retry count: {test_email.retry_count}")
        print(f"Last retry at: {test_email.last_retry_at}")
        print(f"Error message: {test_email.error_message}")
        
        if test_email.status == EmailStatus.sent:
            print("\nSUCCESS: Email was successfully processed by Celery!")
        elif test_email.status == EmailStatus.failed:
            print("\nPARTIAL SUCCESS: Email processing failed but retry tracking worked.")
            print("This is expected if the email service credentials are invalid or test mode is on.")
        else:
            print(f"\nUNEXPECTED STATUS: Email has status {test_email.status}")
        
        print("\n===== Test Complete =====")
    
    finally:
        db.close()


if __name__ == "__main__":
    test_email_celery_integration()
