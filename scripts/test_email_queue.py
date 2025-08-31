#!/usr/bin/env python
"""
Test script for the email queue system with retry mechanism.
This script will:
1. Create a test email in the queue
2. Simulate a failed sending attempt
3. Verify retry fields are properly updated
"""
import sys
import os
from datetime import datetime, timedelta
import asyncio
import uuid

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get test settings before importing any DB-dependent modules
from app.core.config import get_test_settings

# Set up environment for test database
test_settings = get_test_settings()
os.environ["DATABASE_URL"] = test_settings.DATABASE_URL
print(f"\nUsing test database: {test_settings.DATABASE_URL}")

# Now import database modules which will use the test database URL
from app.db.database import init_db, Base
from app.db.models.email_queue import EmailQueue, EmailStatus
from app.db.models.base_model import Base
from app.db.models.user import User
from app.services.email.queue_service import EmailQueueService


def setup_test_db():
    """Setup the test database with required tables"""
    print("\n===== Setting up test database =====\n")
    
    # Initialize database with test settings URL
    engine, SessionLocal, _ = init_db(override_db_url=test_settings.DATABASE_URL)
    
    # Create all tables in the test database
    Base.metadata.create_all(bind=engine)
    print("Created all tables in test database")
    
    return engine, SessionLocal

def process_email_manually(db, email_id):
    """Process an email directly without using the Celery task"""
    from app.services.email.email_service import EmailService
    
    # Get the email from the queue
    email = db.query(EmailQueue).filter(EmailQueue.id == email_id).first()
    if not email:
        print(f"Email with ID {email_id} not found")
        return {"success": False, "error": "Email not found"}
    
    # Create a mock version of the Celery task that operates directly
    print(f"Processing email {email.id} to {email.recipient}")
    
    try:
        # We're not actually sending the email in this test
        # Just simulate the process and update the status
        
        # Simulate the email sending has failed
        print("Simulating email send failure...")
        
        # Update the retry count and last retry timestamp
        email.retry_count += 1
        email.last_retry_at = datetime.now()
        email.status = EmailStatus.failed
        email.error_message = "Test error: Simulated failure"
        db.commit()
        
        print(f"Email processing failed with error: Simulated failure")
        print(f"Updated retry count to {email.retry_count}")
        
        return {"success": False, "error": "Simulated failure"}
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_email_queue():
    """Test the email queue system with retry mechanism"""
    print("\n===== Email Queue System Test =====\n")
    
    # Setup the test database
    _, SessionLocal = setup_test_db()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # 1. Clean up any existing test data
        print("Cleaning up existing test data...")
        
        # Clean up test emails
        test_emails = db.query(EmailQueue).filter(
            EmailQueue.recipient == "test_retry@example.com"
        ).all()
        
        for email in test_emails:
            db.delete(email)
        
        # Clean up test users
        test_user = db.query(User).filter(
            User.email == "test_user@example.com"
        ).first()
        
        if test_user:
            db.delete(test_user)
        
        db.commit()
        print(f"Cleaned up {len(test_emails)} test emails and removed any test users.")
        
        # 1b. Create a test user
        print("\nCreating a test user...")
        test_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="test_user@example.com",
            hashed_password="test_password_hash",
            is_active=True,
            is_admin=False,
            full_name="Test User",
            subscription_status="active"
        )
        
        db.add(test_user)
        db.commit()
        print(f"Created test user with ID: {test_user.id}")
        
        # 2. Create a test email directly in the queue
        print("\nCreating a test email in the queue...")
        test_email = EmailQueue(
            id=uuid.uuid4(),
            user_id=test_user.id,  # Use our newly created test user
            email_type="test_retry",
            recipient="test_retry@example.com",
            subject="Test Email Retry System",
            html_content="<h1>This is a test email for the retry system</h1>",
            text_content="This is a test email for the retry system",
            status=EmailStatus.pending,
            retry_count=0,
            max_retries=3,
            scheduled_for=datetime.now()
        )
        
        db.add(test_email)
        db.commit()
        
        # 3. Query to verify the email was enqueued
        test_email = db.query(EmailQueue).filter(
            EmailQueue.recipient == "test_retry@example.com",
            EmailQueue.email_type == "test_retry"
        ).first()
        
        if not test_email:
            print("ERROR: Test email was not enqueued properly.")
            return
        
        print(f"Email successfully enqueued with ID: {test_email.id}")
        print(f"Initial retry_count: {test_email.retry_count}")
        print(f"Initial max_retries: {test_email.max_retries}")
        
        # 4. Manually simulate processing the email (which will fail)
        print("\nSimulating a failed send attempt...")
        
        # Process the email directly (not through Celery)
        result = process_email_manually(db, test_email.id)
        print(f"Process result: {result}")
        
        # 5. Refresh the email record
        db.refresh(test_email)
        print(f"\nEmail status after processing: {test_email.status}")
        print(f"Retry count: {test_email.retry_count}")
        print(f"Last retry at: {test_email.last_retry_at}")
        
        # 6. Test the retry logic
        if test_email.status == EmailStatus.failed:
            print("\nEmail failed as expected. Testing retry...")
            
            # Force status back to pending for retry
            test_email.status = EmailStatus.pending
            # Backdate the last retry to ensure it's eligible for retry
            test_email.last_retry_at = datetime.now() - timedelta(hours=1)
            db.commit()
            
            # Process again directly
            print("Processing emails again for retry...")
            result = process_email_manually(db, test_email.id)
            print(f"Process result: {result}")
            
            # Refresh the email record
            db.refresh(test_email)
            print(f"\nEmail status after retry: {test_email.status}")
            print(f"Retry count: {test_email.retry_count}")
            print(f"Last retry at: {test_email.last_retry_at}")
        
        print("\n===== Test Complete =====")
    
    finally:
        db.close()


if __name__ == "__main__":
    # Run the migration on the test database first
    print("\n===== Running migrations on test database =====\n")
    
    # Run the migration using the test database URL that was set at the top of the script
    os.system("alembic upgrade head")
    print("Migrations complete\n")
    
    # Run the test
    asyncio.run(test_email_queue())
