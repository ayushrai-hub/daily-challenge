"""
Script to fix problem tags in the database.

This script does the following:
1. Identifies duplicate tags (case-insensitive matching)
2. Merges duplicate tags using the TagMapper service
3. Fixes all problems to use the correct tags
"""
import sys
import os
import uuid
import logging

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

# Then import services after models are loaded
from app.services.tag_mapper import TagMapper, get_tag_mapper
from sqlalchemy import func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_problem_tags():
    """Fix problem tags in the database."""
    # Get DB session - handle the generator properly
    db = next(get_db())
    
    # Get tag mapper
    tag_mapper = get_tag_mapper(db)
    
    # 1. First merge all duplicate tags in the system
    logger.info("Merging duplicate tags in the system...")
    stats = tag_mapper.merge_duplicate_tags()
    logger.info(f"Merged {stats['tags_merged']} tags in {stats['duplicate_sets']} duplicate sets")
    
    # 2. Get all problems
    problems = db.query(Problem).all()
    logger.info(f"Found {len(problems)} problems to process")
    
    # 3. Process each problem
    problems_fixed = 0
    tags_fixed = 0
    
    for problem in problems:
        problem_fixed = False
        
        # Get all existing tags (to avoid duplicates)
        all_tags = db.query(Tag).all()
        tag_map = {tag.name.lower(): tag for tag in all_tags}
        
        # Check each tag for the problem
        for tag in list(problem.tags):  # Use list to allow modification during iteration
            # Check if there's another tag with the same lowercase name
            normalized_name = tag.name.lower()
            
            # If there's a tag with the same name but different ID, use the mapping
            if normalized_name in tag_map and tag_map[normalized_name].id != tag.id:
                correct_tag = tag_map[normalized_name]
                
                # Log the issue
                logger.info(f"Problem '{problem.title}' uses tag '{tag.name}' (ID: {tag.id}) "
                           f"but should use '{correct_tag.name}' (ID: {correct_tag.id})")
                
                # Remove the incorrect tag
                problem.tags.remove(tag)
                
                # Add the correct tag if not already present
                if correct_tag not in problem.tags:
                    problem.tags.append(correct_tag)
                
                # Mark as fixed
                problem_fixed = True
                tags_fixed += 1
        
        if problem_fixed:
            problems_fixed += 1
    
    # Commit changes
    db.commit()
    
    logger.info(f"Fixed {tags_fixed} tag references across {problems_fixed} problems")
    
    # 4. Perform a second pass to normalize tag names
    tags = db.query(Tag).all()
    normalized_count = 0
    
    for tag in tags:
        normalized_name = tag_mapper.normalize_tag_name(tag.name)
        if tag.name != normalized_name:
            logger.info(f"Normalizing tag name: '{tag.name}' -> '{normalized_name}'")
            tag.name = normalized_name
            normalized_count += 1
    
    # Commit changes again
    db.commit()
    
    logger.info(f"Normalized {normalized_count} tag names to proper casing")
    
    # 5. Add correct parent-child relationships
    tags = db.query(Tag).all()
    parent_child_fixed = 0
    
    # Get or create parent categories
    parent_categories = tag_mapper.get_or_create_parent_categories()
    
    for tag in tags:
        # Skip parent categories themselves
        if tag.name in parent_categories.values():
            continue
            
        # Find suitable parent categories
        suitable_categories = tag_mapper.find_suitable_parent_categories(tag.name)
        
        if suitable_categories and not tag.parent_tag_id:
            # Get the first suitable category as main parent
            main_category = suitable_categories[0]
            parent_tag = db.query(Tag).filter(Tag.name == main_category).first()
            
            if parent_tag:
                logger.info(f"Setting parent category for '{tag.name}': '{main_category}'")
                tag.parent_tag_id = parent_tag.id
                parent_child_fixed += 1
    
    # Final commit
    db.commit()
    
    logger.info(f"Fixed {parent_child_fixed} parent-child relationships")
    
    return {
        "duplicate_sets": stats["duplicate_sets"],
        "tags_merged": stats["tags_merged"],
        "problems_fixed": problems_fixed,
        "tags_fixed": tags_fixed,
        "normalized_count": normalized_count,
        "parent_child_fixed": parent_child_fixed
    }

if __name__ == "__main__":
    results = fix_problem_tags()
    
    print("\nTag Cleanup Results:")
    print("=" * 50)
    print(f"Duplicate tag sets found: {results['duplicate_sets']}")
    print(f"Tags merged: {results['tags_merged']}")
    print(f"Problems with fixed tags: {results['problems_fixed']}")
    print(f"Tag references fixed: {results['tags_fixed']}")
    print(f"Tag names normalized: {results['normalized_count']}")
    print(f"Parent-child relationships fixed: {results['parent_child_fixed']}")
    print("=" * 50)
