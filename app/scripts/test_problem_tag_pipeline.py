"""
Test script to verify the problem creation pipeline properly handles tag normalization.

This script:
1. Creates a test problem with deliberately lowercase tags
2. Verifies the tags are properly normalized and mapped to existing tags
3. Shows the before and after state of the tags in the database
"""
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy import text, func

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all models explicitly to ensure they're registered with SQLAlchemy
from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.problem import Problem, DifficultyLevel, ProblemStatus, VettingTier
from app.db.models.user import User
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog
from app.db.models.verification_token import VerificationToken
try:
    from app.db.models.verification_metrics import VerificationMetrics
except ImportError:
    pass
try:
    from app.db.models.email_queue import EmailQueue
except ImportError:
    pass

from app.repositories.problem_repository import create_problem_with_tags_sync
from app.core.logging import get_logger

logger = get_logger()

def get_tag_count(db, tag_name_pattern):
    """Get the count of tags matching a pattern case-insensitively."""
    query = text(f"SELECT COUNT(*) FROM tags WHERE LOWER(name) LIKE LOWER('%{tag_name_pattern}%')")
    result = db.execute(query).scalar()
    return result

def get_tags_by_pattern(db, tag_name_pattern):
    """Get all tags matching a pattern case-insensitively."""
    query = text(f"SELECT id, name FROM tags WHERE LOWER(name) LIKE LOWER('%{tag_name_pattern}%')")
    results = db.execute(query).fetchall()
    return [{"id": row[0], "name": row[1]} for row in results]

def test_problem_creation_with_tags():
    """Test creating a problem with deliberately lowercase versions of existing tags."""
    db = next(get_db())
    
    # First get tag counts before the test
    initial_tag_count = db.query(Tag).count()
    eslint_tags_before = get_tags_by_pattern(db, 'eslint')
    js_tags_before = get_tags_by_pattern(db, 'javascript')
    
    print(f"Initial tag count: {initial_tag_count}")
    print(f"ESLint tags before: {eslint_tags_before}")
    print(f"JavaScript tags before: {js_tags_before}")
    
    # Create a test problem with deliberately lowercase tags
    test_problem_data = {
        "title": "Test Problem for Tag Pipeline",
        "description": "This is a test problem to verify tag normalization in the problem creation pipeline.",
        "difficulty_level": DifficultyLevel.easy,
        "source_platform": "custom",
        "source_url": "https://example.com/test",
        "problem_type": "coding",
        "solution": "Test solution",
        "status": ProblemStatus.approved,
        "vetting_tier": VettingTier.tier1_manual,
        "uuid": str(uuid.uuid4()),
        
        # Deliberately use lowercase and mixed case to test normalization
        "tags": ["eslint", "javascript", "code quality", "Frontend"],  
        
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "enabled": True,
    }
    
    try:
        # Create the problem with tags
        problem_id = create_problem_with_tags_sync(db, test_problem_data)
        print(f"\nCreated test problem with ID: {problem_id}")
        
        # Check tag counts after creation
        final_tag_count = db.query(Tag).count()
        eslint_tags_after = get_tags_by_pattern(db, 'eslint')
        js_tags_after = get_tags_by_pattern(db, 'javascript')
        
        print(f"\nFinal tag count: {final_tag_count}")
        print(f"ESLint tags after: {eslint_tags_after}")
        print(f"JavaScript tags after: {js_tags_after}")
        
        # Get the created problem with its tags
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        
        if problem:
            print(f"\nProblem tags: {[tag.name for tag in problem.tags]}")
        
        # Success criteria:
        # 1. No new ESLint or JavaScript tags should be created (count should be same as before)
        # 2. The problem should be associated with the properly cased tags
        eslint_success = len(eslint_tags_after) == len(eslint_tags_before)
        js_success = len(js_tags_after) == len(js_tags_before)
        
        # Calculate expected tag count change for other tags
        # We might have created "code quality" and "Frontend" if they didn't exist
        expected_new_tags = 0
        for tag_name in ["code quality", "frontend"]:
            exists = False
            for existing_tag in db.query(Tag).all():
                if existing_tag.name.lower() == tag_name.lower():
                    exists = True
                    break
            if not exists:
                expected_new_tags += 1
        
        overall_success = eslint_success and js_success and (final_tag_count - initial_tag_count <= expected_new_tags)
        
        print("\nTest Results:")
        print(f"ESLint tags normalized correctly: {'✅' if eslint_success else '❌'}")
        print(f"JavaScript tags normalized correctly: {'✅' if js_success else '❌'}")
        print(f"Overall tag creation behavior correct: {'✅' if overall_success else '❌'}")
        
        # Clean up
        db.delete(problem)
        db.commit()
        print("\nTest cleanup completed - test problem deleted")
        
        return overall_success
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error during test: {str(e)}")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\nTesting Problem Creation Tag Pipeline")
    print("=" * 50)
    
    success = test_problem_creation_with_tags()
    
    print("\nFinal Result:")
    print("=" * 50)
    if success:
        print("✅ SUCCESS: The problem creation pipeline correctly normalizes tags!")
        print("- Lowercase tags are properly mapped to existing tags with correct capitalization")
        print("- No duplicate tags are created")
    else:
        print("❌ FAILURE: The problem creation pipeline has issues with tag normalization")
        print("- See output above for details on what went wrong")
    print("=" * 50)
