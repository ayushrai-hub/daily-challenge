"""
Test script to verify tag normalization and mapping is working correctly.

This script:
1. Creates a test problem with lowercase versions of existing tags
2. Verifies that the tags are properly normalized and mapped to existing tags
3. Cleans up the test problem after verification
"""
import sys
import os
import uuid
from datetime import datetime

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.logging import get_logger
logger = get_logger()

# Import all models to ensure they're registered with SQLAlchemy
from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.problem import Problem
from app.db.models.user import User
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog
from app.db.models.verification_token import VerificationToken
try:
    from app.db.models.verification_metrics import VerificationMetrics
except ImportError:
    logger.warning("VerificationMetrics model not found, skipping import")
try:
    from app.db.models.email_queue import EmailQueue
except ImportError:
    logger.warning("EmailQueue model not found, skipping import")
from app.repositories.problem_repository import create_problem_with_tags_sync
from app.services.tag_normalizer import TagNormalizer


def test_tag_normalization():
    """Test tag normalization by creating a problem with intentionally lowercase tags."""
    db = next(get_db())
    
    # Get count of tags before test
    tags_before = db.query(Tag).count()
    logger.info(f"Tags before test: {tags_before}")
    
    # Check if ESLint tag exists (it should after our fix)
    eslint_tag = db.query(Tag).filter(Tag.name == "ESLint").first()
    if not eslint_tag:
        logger.error("ESLint tag not found in database. Test preparation failed.")
        return False
    
    logger.info(f"Found ESLint tag with ID: {eslint_tag.id}")
    
    # Create a test problem with deliberately lowercase tags
    # This should trigger tag normalization and mapping
    problem_data = {
        "title": "Test Problem for Tag Normalization",
        "description": "This is a test problem to verify tag normalization.",
        "difficulty": "easy",  # Required field
        "content": "Test content for tag normalization.",
        "source_platform": "custom",
        "source_url": "https://example.com/test",  # Required for validation
        "uuid": str(uuid.uuid4()),
        "tags": ["eslint", "javascript", "code quality"],  # Deliberately using lowercase
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "enabled": True,
        "solution": "Test solution",  # Required field
        "problem_type": "coding",  # Required field
    }
    
    try:
        # Create the problem
        problem_id = create_problem_with_tags_sync(db, problem_data)
        logger.info(f"Created test problem with ID: {problem_id}")
        
        # Retrieve the created problem with its tags
        problem = db.query(Problem).filter(Problem.uuid == problem_id).first()
        if not problem:
            logger.error("Failed to retrieve created problem")
            return False
        
        # Log the tags attached to the problem
        problem_tags = [tag.name for tag in problem.tags]
        logger.info(f"Problem tags: {problem_tags}")
        
        # Check if "ESLint" (proper case) is in the tags
        has_proper_eslint = "ESLint" in problem_tags
        has_lowercase_eslint = "eslint" in problem_tags
        
        logger.info(f"Has proper case ESLint: {has_proper_eslint}")
        logger.info(f"Has lowercase eslint: {has_lowercase_eslint}")
        
        # Verify tag count hasn't increased (no duplicates created)
        tags_after = db.query(Tag).count()
        logger.info(f"Tags after test: {tags_after}")
        logger.info(f"Tag count change: {tags_after - tags_before}")
        
        # Success conditions:
        # 1. The problem has the proper case "ESLint" tag
        # 2. The problem does NOT have the lowercase "eslint" tag
        # 3. Total tag count did not increase (no duplicates created)
        success = has_proper_eslint and not has_lowercase_eslint
        
        # Clean up - delete the test problem
        db.delete(problem)
        db.commit()
        logger.info("Test problem deleted")
        
        return success
        
    except Exception as e:
        logger.error(f"Error during tag normalization test: {str(e)}")
        db.rollback()
        return False


if __name__ == "__main__":
    try:
        result = test_tag_normalization()
        
        print("\nTag Normalization Test Results:")
        print("=" * 50)
        if result:
            print("✅ SUCCESS: Tag normalization is working correctly!")
            print("- Lowercase 'eslint' was properly mapped to existing 'ESLint' tag")
            print("- No duplicate tags were created")
        else:
            print("❌ FAILURE: Tag normalization test failed")
            print("- See logs for details on what went wrong")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Error running test script: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)
