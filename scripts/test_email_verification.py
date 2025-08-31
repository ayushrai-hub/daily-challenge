#!/usr/bin/env python
"""
Test the complete email verification flow in the dev environment.

This script will:
1. Register a test user
2. Check if a verification email is enqueued
3. Simulate verification using the token
4. Verify the user's is_email_verified status is updated
"""
import sys
import time
import json
import uuid
import requests
from datetime import datetime, timedelta
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Optional, List, Tuple

# Use dev database URL
DATABASE_URL = "postgresql://dcq_user:dcq_pass@localhost:5433/dcq_db"

# API URL
API_URL = "http://localhost:8000/api"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_user(test_email: Optional[str] = None, force_new_email: bool = True) -> Dict[str, Any]:
    """
    Create a test user through the registration API.
    
    Args:
        test_email: Optional specific email to use for registration
        force_new_email: If True, append a unique ID to the email to avoid duplicates
    
    Returns:
        Dict with user info and response details
    """
    # Generate unique email if not provided or to make unique
    unique_id = str(uuid.uuid4())[:8]
    
    if not test_email:
        # Use a placeholder email if none provided
        test_email = f"test.user+{unique_id}@example.com"
    elif force_new_email:
        # Add unique identifier to provided email to avoid duplicate registration
        parts = test_email.split('@')
        if len(parts) == 2:
            test_email = f"{parts[0]}+{unique_id}@{parts[1]}"
    
    # Registration data
    registration_data = {
        "email": test_email,
        "password": "StrongP@ssw0rd",
        "full_name": f"Test User {unique_id}"
    }
    
    # Send registration request
    logger.info(f"Registering test user with email: {test_email}")
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json=registration_data
        )
        
        response_data = response.json()
        
        if response.status_code == 201:
            logger.info(f"User registered successfully: {response.status_code}")
            return {
                "success": True,
                "user_id": response_data.get("id"),
                "email": test_email,
                "full_name": registration_data["full_name"],
                "response": response_data
            }
        else:
            logger.error(f"Failed to register user: {response.status_code} - {response_data}")
            return {
                "success": False,
                "error": response_data,
                "status_code": response.status_code
            }
    except Exception as e:
        logger.error(f"Exception during user registration: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def check_verification_email(user_id: str, max_attempts: int = 10) -> Dict[str, Any]:
    """
    Check if a verification email was enqueued for the user.
    
    Args:
        user_id: The ID of the user to check
        max_attempts: Maximum number of attempts to find the email
        
    Returns:
        Dict with email details if found
    """
    logger.info(f"Checking for verification email for user: {user_id}")
    
    # Connect to database
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    # Try multiple times to find the email (it might take time to be enqueued)
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Attempt {attempt}/{max_attempts} to find verification email")
        
        with Session() as session:
            # Query for verification email
            result = session.execute(
                text("""
                SELECT eq.id, eq.email_type, eq.recipient, eq.subject, eq.status, eq.created_at, 
                       vt.id as token_id, vt.token, vt.expires_at, vt.is_used
                FROM email_queue eq
                JOIN verification_tokens vt ON vt.user_id = eq.user_id
                WHERE eq.user_id = :user_id
                AND eq.email_type = 'verification'
                ORDER BY eq.created_at DESC
                LIMIT 1
                """),
                {"user_id": user_id}
            )
            
            row = result.fetchone()
            
            if row:
                logger.info(f"Found verification email (ID: {row.id}) with token (ID: {row.token_id})")
                return {
                    "success": True,
                    "email_id": row.id,
                    "token_id": row.token_id,
                    "token": row.token,
                    "recipient": row.recipient,
                    "expires_at": row.expires_at,
                    "is_used": row.is_used,
                    "email_status": row.status
                }
        
        # Wait before trying again
        time.sleep(1)
    
    logger.error(f"No verification email found after {max_attempts} attempts")
    return {
        "success": False,
        "error": "Verification email not found"
    }

def verify_email_with_token(token: str) -> Dict[str, Any]:
    """
    Verify a user's email using the verification token.
    
    Args:
        token: The verification token
        
    Returns:
        Dict with verification status
    """
    logger.info(f"Verifying email with token: {token[:10]}...")
    
    try:
        response = requests.post(
            f"{API_URL}/auth/verify-email",
            json={"token": token}
        )
        
        response_data = response.json()
        
        if response.status_code == 200:
            logger.info(f"Email verification successful: {response.status_code}")
            return {
                "success": True,
                "response": response_data
            }
        else:
            logger.error(f"Failed to verify email: {response.status_code} - {response_data}")
            return {
                "success": False,
                "error": response_data,
                "status_code": response.status_code
            }
    except Exception as e:
        logger.error(f"Exception during email verification: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def check_user_verification_status(user_id: str) -> Dict[str, Any]:
    """
    Check if a user is marked as verified in the database.
    
    Args:
        user_id: The ID of the user to check
        
    Returns:
        Dict with user verification status
    """
    logger.info(f"Checking verification status for user: {user_id}")
    
    # Connect to database
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Query for user verification status
        result = session.execute(
            text("SELECT email, is_email_verified FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        
        row = result.fetchone()
        
        if row:
            logger.info(f"User {row.email} verification status: {row.is_email_verified}")
            return {
                "success": True,
                "email": row.email,
                "is_verified": row.is_email_verified
            }
        else:
            logger.error(f"User not found with ID: {user_id}")
            return {
                "success": False,
                "error": "User not found"
            }

def test_email_verification_flow(test_email: Optional[str] = None, force_new_email: bool = True):
    """
    Run the complete email verification flow test.
    
    Args:
        test_email: Optional email address to use for the test
        force_new_email: If True, make the email unique to avoid duplicates
    """
    logger.info("\n===== Testing Email Verification Flow =====\n")
    
    # Step 1: Create a test user
    user_result = create_test_user(test_email=test_email, force_new_email=force_new_email)
    if not user_result["success"]:
        logger.error(f"Test failed at step 1: Unable to create test user: {user_result.get('error')}")
        return False
    
    user_id = user_result["user_id"]
    email = user_result["email"]
    logger.info(f"Step 1 completed: Created test user with ID {user_id} and email {email}")
    
    # Step 2: Check for verification email
    email_result = check_verification_email(user_id)
    if not email_result["success"]:
        logger.error("Test failed at step 2: Verification email not found")
        return False
    
    token = email_result["token"]
    logger.info(f"Step 2 completed: Found verification email with token {token[:10]}...")
    
    # Step 3: Verify email with token
    verify_result = verify_email_with_token(token)
    if not verify_result["success"]:
        logger.error("Test failed at step 3: Unable to verify email with token")
        return False
    
    logger.info("Step 3 completed: Email verification API call successful")
    
    # Step 4: Check user verification status
    status_result = check_user_verification_status(user_id)
    if not status_result["success"]:
        logger.error("Test failed at step 4: Unable to check user verification status")
        return False
    
    if not status_result["is_verified"]:
        logger.error("Test failed at step 4: User is not marked as verified in the database")
        return False
    
    logger.info("Step 4 completed: User is correctly marked as verified in the database")
    
    logger.info("\n===== Email Verification Flow Test Results =====")
    logger.info("✅ All steps completed successfully")
    logger.info(f"✅ User {email} was registered and verified")
    logger.info(f"✅ Verification token was generated and processed")
    logger.info(f"✅ User is correctly marked as verified in the database")
    
    return True

if __name__ == "__main__":
    # Make sure FastAPI server is running before executing this test
    print("This test requires the FastAPI server to be running on http://localhost:8000")
    print("Note: Email delivery won't actually happen unless you provide a real email")
    print("\nOptions:")
    print("1. Use a test email with an auto-generated unique ID (won't receive actual email)")
    print("2. Enter a real email address (will be made unique by adding +tag)")
    print("3. Enter a real email address (exactly as entered - may fail if already registered)")
    print("\nEnter your choice (1-3) or Ctrl+C to cancel:")
    
    try:
        choice = input().strip()
        test_email = None
        force_new_email = True
        
        if choice == "2":
            print("\nEnter the email address:")
            test_email = input().strip()
            force_new_email = True
        elif choice == "3":
            print("\nEnter the email address:")
            test_email = input().strip()
            force_new_email = False
        elif choice != "1":
            print("Invalid choice. Using option 1 (test email with auto-generated ID).")
        
        print("\nStarting test...\n")
        success = test_email_verification_flow(test_email=test_email, force_new_email=force_new_email)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(0)
