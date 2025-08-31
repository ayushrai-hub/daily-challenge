#!/usr/bin/env python
"""
Verify the email queue fields in the development database.
This script will:
1. Query the email_queue table to check if the retry fields exist
2. Print some statistics about emails in the system
"""
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models.email_queue import EmailQueue, EmailStatus
from sqlalchemy import func, desc


def verify_email_queue_fields():
    """Verify the email queue fields in the development database"""
    print("\n===== Email Queue Field Verification =====\n")
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # 1. Check if the table exists and has our new fields
        print("Checking email_queue table structure...\n")
        
        # Try to access one record
        email = db.query(EmailQueue).first()
        
        if not email:
            print("No emails found in the queue table.")
            print("The table exists but is empty.")
        else:
            print("Email queue table exists and contains records.")
            
            # Check new fields
            has_retry_count = hasattr(email, 'retry_count')
            has_last_retry_at = hasattr(email, 'last_retry_at')
            has_max_retries = hasattr(email, 'max_retries')
            has_delivery_data = hasattr(email, 'delivery_data')
            
            print(f"Has retry_count field: {has_retry_count}")
            print(f"Has last_retry_at field: {has_last_retry_at}")
            print(f"Has max_retries field: {has_max_retries}")
            print(f"Has delivery_data field: {has_delivery_data}")
            
            if all([has_retry_count, has_last_retry_at, has_max_retries, has_delivery_data]):
                print("\nSUCCESS: All required fields exist in the email_queue table!")
            else:
                print("\nWARNING: Some fields are missing from the email_queue table.")
        
        # 2. Get some stats about emails in the system
        print("\nEmail Queue Statistics:")
        
        total_emails = db.query(func.count(EmailQueue.id)).scalar()
        print(f"Total emails in queue: {total_emails}")
        
        # Count by status
        status_counts = db.query(
            EmailQueue.status, 
            func.count(EmailQueue.id)
        ).group_by(EmailQueue.status).all()
        
        print("\nEmails by status:")
        for status, count in status_counts:
            print(f"  {status}: {count}")
        
        # Get info about retried emails if there are any
        retried_emails = db.query(EmailQueue).filter(
            EmailQueue.retry_count > 0
        ).order_by(desc(EmailQueue.retry_count)).limit(5).all()
        
        if retried_emails:
            print("\nTop 5 retried emails:")
            for email in retried_emails:
                print(f"  ID: {email.id}")
                print(f"  Status: {email.status}")
                print(f"  Retry count: {email.retry_count}")
                print(f"  Last retry at: {email.last_retry_at}")
                print(f"  Max retries: {email.max_retries}")
                print()
        else:
            print("\nNo retried emails found in the system yet.")
        
        print("\n===== Verification Complete =====")
    
    finally:
        db.close()


if __name__ == "__main__":
    verify_email_queue_fields()
