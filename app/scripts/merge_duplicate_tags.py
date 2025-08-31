"""
Script to identify and merge duplicate tags in the database.

This script:
1. Finds tags that have the same name when compared case-insensitively
2. For each set of duplicates, selects one canonical tag to keep
3. Migrates all problem relationships to the canonical tag
4. Deletes the duplicate tags
"""
import sys
import os
import uuid
import logging
from collections import defaultdict

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all models explicitly to ensure they're registered with SQLAlchemy
from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.problem import Problem
from app.db.models.user import User
from app.db.models.email_queue import EmailQueue
from app.db.models.content_source import ContentSource
from app.db.models.delivery_log import DeliveryLog
from app.db.models.verification_token import VerificationToken
from app.db.models.verification_metrics import VerificationMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def merge_duplicate_tags():
    """Identify and merge duplicate tags in the database."""
    # Get DB session - handle the generator properly
    db = next(get_db())
    
    # Get all tags
    all_tags = db.query(Tag).all()
    logger.info(f"Found {len(all_tags)} tags in the database")
    
    # Group tags by lowercase name
    tags_by_lowercase = defaultdict(list)
    for tag in all_tags:
        lowercase_name = tag.name.lower()
        tags_by_lowercase[lowercase_name].append(tag)
    
    # Find duplicates (tags with the same lowercase name)
    duplicates = {name: tags for name, tags in tags_by_lowercase.items() if len(tags) > 1}
    
    if not duplicates:
        logger.info("No duplicate tags found")
        return {"duplicate_sets": 0, "merged_tags": 0}
    
    logger.info(f"Found {len(duplicates)} sets of duplicate tags")
    
    # Process each set of duplicates
    merged_count = 0
    
    for lowercase_name, tags in duplicates.items():
        # Sort tags by priority to choose the canonical one:
        # 1. Prefer tags with more problems associated
        # 2. Prefer tags with proper title case over weird casing
        # 3. Prefer tags with parent relationships
        
        tags.sort(key=lambda t: (
            -len(getattr(t, 'problems', [])),  # Negative so more problems = higher priority
            1 if t.name == t.name.title() else 0,  # Title case preferred
            1 if t.parent_tag_id else 0  # Having a parent is preferred
        ), reverse=True)
        
        canonical_tag = tags[0]
        logger.info(f"Selected canonical tag for '{lowercase_name}': '{canonical_tag.name}' (id: {canonical_tag.id})")
        
        # Process each duplicate tag
        for duplicate in tags[1:]:
            logger.info(f"Merging '{duplicate.name}' (id: {duplicate.id}) into '{canonical_tag.name}'")
            
            # Migrate problem relationships
            if hasattr(duplicate, 'problems') and duplicate.problems is not None:
                # Make sure problems is iterable
                if hasattr(duplicate.problems, '__iter__'):
                    for problem in duplicate.problems:
                        if canonical_tag not in problem.tags:
                            problem.tags.append(canonical_tag)
                            logger.info(f"Moved problem '{problem.title}' to canonical tag")
                else:
                    logger.warning(f"Problems attribute is not iterable for tag {duplicate.name}")
            
            # Migrate child tag relationships
            if hasattr(duplicate, 'children') and duplicate.children is not None:
                # Make sure children is iterable
                if hasattr(duplicate.children, '__iter__'):
                    for child in duplicate.children:
                        child.parent_tag_id = canonical_tag.id
                        logger.info(f"Updated child tag '{child.name}' to use canonical parent")
                else:
                    logger.warning(f"Children attribute is not iterable for tag {duplicate.name}")
            
            # Delete the duplicate tag
            db.delete(duplicate)
            merged_count += 1
    
    # Commit changes
    try:
        db.commit()
        logger.info(f"Successfully merged {merged_count} duplicate tags")
    except Exception as e:
        db.rollback()
        logger.error(f"Error merging tags: {str(e)}")
        raise
    
    return {"duplicate_sets": len(duplicates), "merged_tags": merged_count}

if __name__ == "__main__":
    try:
        results = merge_duplicate_tags()
        
        print("\nDuplicate Tag Merge Results:")
        print("=" * 50)
        print(f"Duplicate tag sets found: {results['duplicate_sets']}")
        print(f"Tags merged: {results['merged_tags']}")
        print("=" * 50)
    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)
