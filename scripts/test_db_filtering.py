#!/usr/bin/env python3
"""
Script to directly test filtering functionality against the database
using SQLAlchemy Core rather than ORM to avoid circular dependencies.
"""

import sys
import os
import uuid
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Boolean, inspect

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

# Import settings but avoid importing models to prevent circular dependencies
from app.core.config import settings

def setup_test():
    """Setup test connection and data"""
    # Connect directly to the database
    engine = create_engine(settings.DATABASE_URL)
    conn = engine.connect()
    
    # Generate a unique identifier for this test run
    test_id = str(uuid.uuid4())[:8]
    test_prefix = f"filter_test_{test_id}"
    
    # Create test users
    timestamp = datetime.now().isoformat()
    
    # Create three test users with different attributes
    try:
        # 1. Active user
        conn.execute(text(
            "INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
            "VALUES (:email, :pwd, :active, :status, :created, :updated)"
        ), {
            "email": f"{test_prefix}_active@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": True,
            "status": "active",
            "created": timestamp,
            "updated": timestamp
        })
        
        # 2. Inactive user
        conn.execute(text(
            "INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
            "VALUES (:email, :pwd, :active, :status, :created, :updated)"
        ), {
            "email": f"{test_prefix}_inactive@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": False,
            "status": "active",
            "created": timestamp,
            "updated": timestamp
        })
        
        # 3. Paused subscription user
        conn.execute(text(
            "INSERT INTO users (email, hashed_password, is_active, subscription_status, created_at, updated_at) "
            "VALUES (:email, :pwd, :active, :status, :created, :updated)"
        ), {
            "email": f"{test_prefix}_paused@example.com",
            "pwd": "$2b$12$testpasswordhash",
            "active": True,
            "status": "paused",
            "created": timestamp,
            "updated": timestamp
        })
        
        conn.commit()
        logger.info(f"Created three test users with prefix {test_prefix}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating test data: {e}")
        raise
    
    return engine, conn, test_prefix

def cleanup_test(conn, test_prefix):
    """Clean up test data"""
    try:
        result = conn.execute(text(
            "DELETE FROM users WHERE email LIKE :prefix"
        ), {
            "prefix": f"{test_prefix}%"
        })
        conn.commit()
        logger.info(f"Cleaned up {result.rowcount} test users")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error cleaning up test data: {e}")

def test_filtering():
    """Test filtering functionality"""
    engine = None
    conn = None
    test_prefix = None
    
    try:
        # Setup test
        engine, conn, test_prefix = setup_test()
        
        # Test 1: Filter by exact email
        logger.info("\nTEST 1: Filter by exact email")
        email = f"{test_prefix}_active@example.com"
        result = conn.execute(text(
            "SELECT * FROM users WHERE email = :email"
        ), {
            "email": email
        })
        users = result.fetchall()
        logger.info(f"Found {len(users)} users with email={email}")
        assert len(users) == 1, f"Expected 1 user, found {len(users)}"
        logger.info("✅ Email filtering works")
        
        # Test 2: Filter by is_active
        logger.info("\nTEST 2: Filter by is_active")
        active_result = conn.execute(text(
            "SELECT * FROM users WHERE email LIKE :prefix AND is_active = true"
        ), {
            "prefix": f"{test_prefix}%"
        })
        active_users = active_result.fetchall()
        
        inactive_result = conn.execute(text(
            "SELECT * FROM users WHERE email LIKE :prefix AND is_active = false"
        ), {
            "prefix": f"{test_prefix}%"
        })
        inactive_users = inactive_result.fetchall()
        
        logger.info(f"Found {len(active_users)} active users and {len(inactive_users)} inactive users")
        assert len(active_users) == 2, f"Expected 2 active users, found {len(active_users)}"
        assert len(inactive_users) == 1, f"Expected 1 inactive user, found {len(inactive_users)}"
        logger.info("✅ is_active filtering works")
        
        # Test 3: Filter by subscription_status
        logger.info("\nTEST 3: Filter by subscription_status")
        paused_result = conn.execute(text(
            "SELECT * FROM users WHERE email LIKE :prefix AND subscription_status = 'paused'"
        ), {
            "prefix": f"{test_prefix}%"
        })
        paused_users = paused_result.fetchall()
        
        active_sub_result = conn.execute(text(
            "SELECT * FROM users WHERE email LIKE :prefix AND subscription_status = 'active'"
        ), {
            "prefix": f"{test_prefix}%"
        })
        active_sub_users = active_sub_result.fetchall()
        
        logger.info(f"Found {len(paused_users)} paused subscription users")
        logger.info(f"Found {len(active_sub_users)} active subscription users")
        assert len(paused_users) == 1, f"Expected 1 paused subscription user, found {len(paused_users)}"
        assert len(active_sub_users) == 2, f"Expected 2 active subscription users, found {len(active_sub_users)}"
        logger.info("✅ subscription_status filtering works")
        
        # Test 4: Multiple filters combined
        logger.info("\nTEST 4: Multiple filters combined")
        combined_result = conn.execute(text(
            "SELECT * FROM users WHERE email LIKE :prefix AND is_active = true AND subscription_status = 'paused'"
        ), {
            "prefix": f"{test_prefix}%"
        })
        combined_users = combined_result.fetchall()
        
        logger.info(f"Found {len(combined_users)} users matching multiple filters")
        assert len(combined_users) == 1, f"Expected 1 user matching multiple filters, found {len(combined_users)}"
        logger.info("✅ Combined filtering works")
        
        logger.info("\n✅ All filtering tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if conn and test_prefix:
            cleanup_test(conn, test_prefix)
        if conn:
            conn.close()
        if engine:
            engine.dispose()

if __name__ == "__main__":
    logger.info("Starting direct database filtering test...")
    test_filtering()
    logger.info("Test completed")
