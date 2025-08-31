#!/usr/bin/env python
"""
Test the protected routes that require email verification.

This script will:
1. Register a test user
2. Check if a verification email is enqueued
3. Try accessing protected endpoints BEFORE verification (should fail with 403)
4. Verify the email using the token
5. Try accessing protected endpoints AFTER verification (should succeed)

This allows testing the complete email verification security flow.
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
                "password": registration_data["password"],  # Store password for login
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

def login_user(email: str, password: str) -> Dict[str, Any]:
    """
    Login a user to get authentication token.
    
    Args:
        email: User email
        password: User password
    
    Returns:
        Dict with token info if successful
    """
    login_data = {
        "username": email,  # FastAPI OAuth2 uses 'username' for email
        "password": password
    }
    
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data=login_data,  # Form data, not JSON for OAuth2 password flow
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return {
                "success": True,
                "access_token": token_data.get("access_token"),
                "token_type": token_data.get("token_type")
            }
        else:
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
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
                JOIN verification_tokens vt ON vt.user_id = :user_id
                WHERE eq.user_id = :user_id 
                  AND eq.email_type = 'verification'
                  AND eq.status = 'pending'
                ORDER BY eq.created_at DESC
                LIMIT 1
                """),
                {"user_id": user_id}
            )
            
            row = result.fetchone()
            if row:
                logger.info(f"Verification email found for user {user_id}")
                return {
                    "success": True,
                    "email_id": str(row.id),
                    "recipient": row.recipient,
                    "subject": row.subject,
                    "token": row.token,
                    "token_id": str(row.token_id),
                    "expires_at": row.expires_at
                }
        
        # Wait before trying again
        if attempt < max_attempts:
            time.sleep(1)
    
    logger.error(f"No verification email found for user {user_id} after {max_attempts} attempts")
    return {
        "success": False,
        "error": "No verification email found"
    }

def verify_email_with_token(token: str) -> Dict[str, Any]:
    """
    Verify a user's email using the verification token.
    
    Args:
        token: The verification token
        
    Returns:
        Dict with verification status
    """
    logger.info(f"Verifying email with token {token[:10]}...")
    
    try:
        response = requests.post(
            f"{API_URL}/auth/verify-email",
            json={"token": token}
        )
        
        if response.status_code == 200:
            logger.info("Email verification successful")
            return {
                "success": True,
                "response": response.json()
            }
        else:
            logger.error(f"Email verification failed: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": response.text,
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
        result = session.execute(
            text("SELECT id, email, is_email_verified FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        
        row = result.fetchone()
        if row:
            logger.info(f"User verification status: {'verified' if row.is_email_verified else 'not verified'}")
            return {
                "success": True,
                "user_id": str(row.id),
                "email": row.email,
                "is_verified": row.is_email_verified
            }
        else:
            logger.error(f"User not found with ID: {user_id}")
            return {
                "success": False,
                "error": "User not found"
            }

def test_protected_endpoints(token: str, should_succeed: bool) -> Dict[str, Any]:
    """
    Test access to protected endpoints that require email verification.
    
    Args:
        token: The authentication token
        should_succeed: Whether the requests should succeed
    
    Returns:
        Dict with test results
    """
    auth_header = {"Authorization": f"Bearer {token}"}
    expected_status = 200 if should_succeed else 403
    expected_result = "succeed" if should_succeed else "fail with 403"
    
    logger.info(f"Testing protected endpoints (expecting them to {expected_result})")
    
    results = {}
    
    # Test 1: User profile endpoint
    try:
        logger.info("Testing /users/me/profile endpoint...")
        response = requests.get(f"{API_URL}/users/me/profile", headers=auth_header)
        success = (response.status_code == expected_status)
        
        results["profile"] = {
            "success": success,
            "status_code": response.status_code,
            "has_verification_header": "X-Email-Verification-Required" in response.headers
        }
        
        if success:
            logger.info(f"✅ Profile endpoint test {'succeeded' if should_succeed else 'failed'} as expected")
        else:
            logger.error(f"❌ Profile endpoint returned {response.status_code}, expected {expected_status}")
            
    except Exception as e:
        results["profile"] = {"success": False, "error": str(e)}
    
    # Test 2: Subscriptions endpoint
    try:
        logger.info("Testing /subscriptions/me endpoint...")
        response = requests.get(f"{API_URL}/subscriptions/me", headers=auth_header)
        success = (response.status_code == expected_status)
        
        results["subscriptions"] = {
            "success": success,
            "status_code": response.status_code,
            "has_verification_header": "X-Email-Verification-Required" in response.headers
        }
        
        if success:
            logger.info(f"✅ Subscriptions endpoint test {'succeeded' if should_succeed else 'failed'} as expected")
        else:
            logger.error(f"❌ Subscriptions endpoint returned {response.status_code}, expected {expected_status}")
            
    except Exception as e:
        results["subscriptions"] = {"success": False, "error": str(e)}
    
    # Test 3: Problems endpoint
    try:
        logger.info("Testing /problems endpoint...")
        response = requests.get(f"{API_URL}/problems", headers=auth_header)
        success = (response.status_code == expected_status)
        
        results["problems"] = {
            "success": success,
            "status_code": response.status_code,
            "has_verification_header": "X-Email-Verification-Required" in response.headers
        }
        
        if success:
            logger.info(f"✅ Problems endpoint test {'succeeded' if should_succeed else 'failed'} as expected")
        else:
            logger.error(f"❌ Problems endpoint returned {response.status_code}, expected {expected_status}")
            
    except Exception as e:
        results["problems"] = {"success": False, "error": str(e)}
    
    # Calculate overall success
    overall_success = all(
        (r["success"] and r["status_code"] == expected_status) 
        for r in results.values() 
        if isinstance(r, dict) and "status_code" in r
    )
    
    results["overall_success"] = overall_success
    
    if overall_success:
        logger.info(f"✅ All protected endpoint tests {'succeeded' if should_succeed else 'failed'} as expected")
    else:
        logger.error("❌ Some endpoint tests did not behave as expected")
    
    return results

def test_verification_protection_flow():
    """
    Test the complete flow including protected routes before and after verification.
    """
    logger.info("\n===== Testing Email Verification Protection Flow =====\n")
    
    # Step 1: Create a test user
    user_result = create_test_user()
    if not user_result["success"]:
        logger.error(f"Test failed at step 1: Unable to create test user: {user_result.get('error')}")
        return False
    
    user_id = user_result["user_id"]
    email = user_result["email"]
    password = user_result["password"]
    logger.info(f"Step 1 completed: Created test user with ID {user_id} and email {email}")
    
    # Step 2: Login to get auth token
    login_result = login_user(email, password)
    if not login_result["success"]:
        logger.error(f"Test failed at step 2: Unable to login: {login_result.get('error')}")
        return False
    
    token = login_result["access_token"]
    logger.info(f"Step 2 completed: Logged in successfully, received auth token")
    
    # Step 3: Test protected endpoints BEFORE verification (should fail with 403)
    before_results = test_protected_endpoints(token, should_succeed=False)
    if not before_results["overall_success"]:
        logger.error("Test failed at step 3: Protected endpoints did not fail as expected")
        return False
    
    logger.info("Step 3 completed: Protected endpoints correctly returned 403 before verification")
    
    # Step 4: Check for verification email
    email_result = check_verification_email(user_id)
    if not email_result["success"]:
        logger.error("Test failed at step 4: Verification email not found")
        return False
    
    verification_token = email_result["token"]
    logger.info(f"Step 4 completed: Found verification email with token {verification_token[:10]}...")
    
    # Step 5: Verify email with token
    verify_result = verify_email_with_token(verification_token)
    if not verify_result["success"]:
        logger.error("Test failed at step 5: Unable to verify email with token")
        return False
    
    logger.info("Step 5 completed: Email verification successful")
    
    # Step 6: Check user verification status
    status_result = check_user_verification_status(user_id)
    if not status_result["success"]:
        logger.error("Test failed at step 6: Unable to check user verification status")
        return False
    
    if not status_result["is_verified"]:
        logger.error("Test failed at step 6: User is not marked as verified in the database")
        return False
    
    logger.info("Step 6 completed: User is correctly marked as verified in the database")
    
    # Step 7: Test protected endpoints AFTER verification (should succeed)
    after_results = test_protected_endpoints(token, should_succeed=True)
    if not after_results["overall_success"]:
        logger.error("Test failed at step 7: Protected endpoints did not succeed as expected after verification")
        return False
    
    logger.info("Step 7 completed: Protected endpoints correctly succeeded after verification")
    
    logger.info("\n===== Email Verification Protection Flow Test Results =====")
    logger.info("✅ All steps completed successfully")
    logger.info(f"✅ User {email} was registered and verified")
    logger.info(f"✅ Protected endpoints correctly denied access before verification")
    logger.info(f"✅ Protected endpoints correctly granted access after verification")
    
    return True

if __name__ == "__main__":
    # Make sure FastAPI server is running before executing this test
    print("This test requires the FastAPI server to be running on http://localhost:8000")
    print("The test will verify that the email verification protection is working correctly")
    print("Press Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
        print("\nStarting test...\n")
        success = test_verification_protection_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest cancelled.")
        sys.exit(0)
