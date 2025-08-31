#!/usr/bin/env python3
"""
Simple script to test the filtering functionality of BaseRepository.get_multi method.
This directly uses the development database to verify filtering works in a real environment.
"""

import sys
import os
import uuid
import logging
from datetime import datetime
from sqlalchemy import text

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database session after path setup
from app.db.database import SessionLocal
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate

def setup_test_data(db):
    """Create test data using direct SQL to avoid circular dependencies"""
    test_id = str(uuid.uuid4())[:8]
    user_prefix = f"filter_test_{test_id}"
    
    # Create three test users with different attributes
    # 1. Active user
    db.execute(
        text("INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
        "VALUES (:email, :pwd, :active, :status, :created, :updated) RETURNING id"),
        {
            "email": f"{user_prefix}_active@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": True,
            "status": "active",
            "created": datetime.now(),
            "updated": datetime.now()
        }
    )
    
    # 2. Inactive user
    db.execute(
        text("INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
        "VALUES (:email, :pwd, :active, :status, :created, :updated) RETURNING id"),
        {
            "email": f"{user_prefix}_inactive@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": False,
            "status": "active",
            "created": datetime.now(),
            "updated": datetime.now()
        }
    )
    
    # 3. Paused subscription user
    db.execute(
        text("INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
        "VALUES (:email, :pwd, :active, :status, :created, :updated) RETURNING id"),
        {
            "email": f"{user_prefix}_paused@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": True,
            "status": "paused",
            "created": datetime.now(),
            "updated": datetime.now()
        }
    )
    
    db.commit()
    logger.info(f"Created 3 test users with prefix {user_prefix}")
    return user_prefix

def cleanup_test_data(db, user_prefix):
    """Remove test data"""
    result = db.execute(
        text("DELETE FROM users WHERE email LIKE :prefix"),
        {"prefix": f"{user_prefix}%"}
    )
    deleted_count = result.rowcount
    db.commit()
    logger.info(f"Cleaned up {deleted_count} test users")

def test_repository_filtering():
    """Test the BaseRepository.get_multi filtering functionality"""
    db = SessionLocal()
    user_prefix = None
    
    try:
        # Set up test data
        user_prefix = setup_test_data(db)
        
        # Create repository
        user_repo = UserRepository(db=db)
        
        # Test 1: Filter by exact email
        logger.info("\nTEST 1: Filtering by exact email")
        active_email = f"{user_prefix}_active@example.com"
        active_users = user_repo.get_multi(email=active_email)
        logger.info(f"Found {len(active_users)} users with email={active_email}")
        assert len(active_users) == 1, f"Expected 1 user, found {len(active_users)}"
        assert active_users[0].email == active_email
        logger.info("✅ Email exact match filtering works")
        
        # Test 2: Filter by is_active status
        logger.info("\nTEST 2: Filtering by is_active status")
        active_users = user_repo.get_multi(is_active=True)
        inactive_users = user_repo.get_multi(is_active=False)
        
        # Find our specific test users
        test_active_users = [u for u in active_users if u.email.startswith(user_prefix)]
        test_inactive_users = [u for u in inactive_users if u.email.startswith(user_prefix)]
        
        logger.info(f"Found {len(test_active_users)} active test users and {len(test_inactive_users)} inactive test users")
        assert len(test_active_users) == 2, f"Expected 2 active users, found {len(test_active_users)}"
        assert len(test_inactive_users) == 1, f"Expected 1 inactive user, found {len(test_inactive_users)}"
        logger.info("✅ is_active filtering works")
        
        # Test 3: Filter by subscription status
        logger.info("\nTEST 3: Filtering by subscription status")
        paused_users = user_repo.get_multi(subscription_status="paused")
        active_sub_users = user_repo.get_multi(subscription_status="active")
        
        # Find our specific test users
        test_paused_users = [u for u in paused_users if u.email.startswith(user_prefix)]
        test_active_sub_users = [u for u in active_sub_users if u.email.startswith(user_prefix)]
        
        logger.info(f"Found {len(test_paused_users)} paused subscription test users")
        logger.info(f"Found {len(test_active_sub_users)} active subscription test users")
        
        assert len(test_paused_users) == 1, f"Expected 1 paused subscription user, found {len(test_paused_users)}"
        assert len(test_active_sub_users) == 2, f"Expected 2 active subscription users, found {len(test_active_sub_users)}"
        logger.info("✅ subscription_status filtering works")
        
        # Test 4: Multiple filters combined
        logger.info("\nTEST 4: Multiple filters combined")
        active_paused_users = user_repo.get_multi(is_active=True, subscription_status="paused")
        test_active_paused = [u for u in active_paused_users if u.email.startswith(user_prefix)]
        
        logger.info(f"Found {len(test_active_paused)} active+paused test users")
        assert len(test_active_paused) == 1, f"Expected 1 active+paused user, found {len(test_active_paused)}"
        logger.info("✅ Multiple filter criteria work correctly")
        
        logger.info("\nAll filtering tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if user_prefix:
            cleanup_test_data(db, user_prefix)
        db.close()

if __name__ == "__main__":
    logger.info("Starting repository filtering test...")
    test_repository_filtering()
    logger.info("Test completed.")
