#!/usr/bin/env python3
"""
Script to test the filtering functionality of BaseRepository.get_multi method
using an in-memory SQLite database for isolated testing.
"""

import sys
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

# Create an in-memory SQLite database for testing
Base = declarative_base()

# Define a simple User model for testing
class TestUser(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    subscription_status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Define Pydantic schemas for Create and Update operations
class UserCreate(BaseModel):
    email: str
    hashed_password: str
    is_active: bool = True
    subscription_status: str = "active"

class UserUpdate(BaseModel):
    email: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_status: Optional[str] = None

# Import the repository class to test
from app.repositories.base import BaseRepository

# Create a repository class for our test user model
class UserRepository(BaseRepository[TestUser, UserCreate, UserUpdate]):
    def __init__(self, db):
        super().__init__(model=TestUser, db=db)

def setup_test_db():
    """Set up an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def test_repository_filtering():
    """Test the BaseRepository get_multi filtering functionality"""
    # Set up the database and repository
    db = setup_test_db()
    user_repo = UserRepository(db=db)
    test_users = []
    
    try:
        # Create test users with different attributes
        logger.info("Creating test users...")
        
        # Generate unique ID for this test run
        test_id = str(uuid.uuid4())[:8]
        
        # Create test users using direct SQL model instantiation to avoid schema validation
        test_users = [
            TestUser(
                email=f"filter_test_{test_id}_active@example.com",
                hashed_password="testpwd",
                is_active=True,
                subscription_status="active"
            ),
            TestUser(
                email=f"filter_test_{test_id}_inactive@example.com",
                hashed_password="testpwd",
                is_active=False,
                subscription_status="active"
            ),
            TestUser(
                email=f"filter_test_{test_id}_paused@example.com",
                hashed_password="testpwd",
                is_active=True,
                subscription_status="paused"
            )
        ]
        
        for user in test_users:
            db.add(user)
        db.commit()
        
        # Refresh to ensure IDs are populated
        for user in test_users:
            db.refresh(user)
            
        # Get all users to verify data is there
        all_users = user_repo.get_multi()
        logger.info(f"Total users in test database: {len(all_users)}")
        
        # Test 1: Filter by exact email
        logger.info("\nTest 1: Filter by exact email")
        email_to_find = test_users[0].email
        filtered_by_email = user_repo.get_multi(email=email_to_find)
        logger.info(f"Found {len(filtered_by_email)} users with email={email_to_find}")
        assert len(filtered_by_email) == 1, f"Expected 1 user, found {len(filtered_by_email)}"
        assert filtered_by_email[0].email == email_to_find
        logger.info("✅ Email filtering works correctly")
            
        # Test 2: Filter by is_active field
        logger.info("\nTest 2: Filter by is_active")
        active_users = user_repo.get_multi(is_active=True)
        inactive_users = user_repo.get_multi(is_active=False)
        
        # Count our test users that match each criteria
        expected_active = len([u for u in test_users if u.is_active])
        expected_inactive = len([u for u in test_users if not u.is_active])
        
        assert len(active_users) == expected_active, f"Expected {expected_active} active users, found {len(active_users)}"
        assert len(inactive_users) == expected_inactive, f"Expected {expected_inactive} inactive users, found {len(inactive_users)}"
        logger.info(f"✅ is_active filtering works (found {len(active_users)} active, {len(inactive_users)} inactive)")
            
        # Test 3: Filter by subscription_status
        logger.info("\nTest 3: Filter by subscription_status")
        paused_users = user_repo.get_multi(subscription_status="paused")
        active_sub_users = user_repo.get_multi(subscription_status="active")
        
        expected_paused = len([u for u in test_users if u.subscription_status == "paused"])
        expected_active_sub = len([u for u in test_users if u.subscription_status == "active"])
        
        assert len(paused_users) == expected_paused, f"Expected {expected_paused} paused users, found {len(paused_users)}"
        assert len(active_sub_users) == expected_active_sub, f"Expected {expected_active_sub} active subscription users, found {len(active_sub_users)}"
        logger.info(f"✅ subscription_status filtering works (found {len(paused_users)} paused, {len(active_sub_users)} active)")
        
        # Test 4: Multiple filters combined
        logger.info("\nTest 4: Multiple filters combined")
        active_paused_users = user_repo.get_multi(is_active=True, subscription_status="paused")
        expected = len([u for u in test_users if u.is_active and u.subscription_status == "paused"])
        assert len(active_paused_users) == expected, f"Expected {expected} active paused users, found {len(active_paused_users)}"
        logger.info(f"✅ Multiple filter criteria work correctly (found {len(active_paused_users)} matches)")
        
        logger.info("\n✅ All filter tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    finally:
        # Clean up test users
        try:
            for user in test_users:
                db.delete(user)
            db.commit()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        db.close()

if __name__ == "__main__":
    logger.info("Starting repository filtering test with in-memory database...")
    test_repository_filtering()
    logger.info("Test completed")
