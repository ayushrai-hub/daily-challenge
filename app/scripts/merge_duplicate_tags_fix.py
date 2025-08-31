"""
Enhanced script to identify and merge duplicate tags in the database.

This script:
1. Finds tags that have the same name when compared case-insensitively
2. For each set of duplicates, selects one canonical tag to keep (preferring proper casing)
3. Migrates all problem relationships to the canonical tag
4. Deletes the duplicate tags
"""
import sys
import os
import logging
from collections import defaultdict
from sqlalchemy import func

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up logging
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

from app.services.tag_normalizer import TagNormalizer


def find_duplicate_tags(db):
    """Find all duplicate tags (case-insensitive match)."""
    # Get all tags
    tags = db.query(Tag).all()
    logger.info(f"Found {len(tags)} tags in database")
    
    # Group tags by lowercase name
    tag_groups = defaultdict(list)
    for tag in tags:
        tag_groups[tag.name.lower()].append(tag)
    
    # Filter to only groups with duplicates
    duplicate_groups = {k: v for k, v in tag_groups.items() if len(v) > 1}
    
    if not duplicate_groups:
        logger.info("No duplicate tags found")
        return {}
    
    logger.info(f"Found {len(duplicate_groups)} groups of duplicate tags")
    for name, dupes in duplicate_groups.items():
        logger.info(f"Duplicate group '{name}': {', '.join(t.name for t in dupes)}")
    
    return duplicate_groups


def select_canonical_tag(tag_group):
    """Select the canonical tag from a group of duplicates."""
    # Prefer tag with proper capitalization (if it exists)
    normalizer = TagNormalizer()
    normalized_name = normalizer._normalize_known_technology(tag_group[0].name.lower())
    
    # First, look for exact match with normalized name
    for tag in tag_group:
        if tag.name == normalized_name:
            return tag
    
    # Otherwise, prefer the one with most problems attached
    return max(tag_group, key=lambda t: len(t.problems) if t.problems else 0)


def merge_duplicate_tags(db):
    """Merge duplicate tags."""
    duplicate_groups = find_duplicate_tags(db)
    
    if not duplicate_groups:
        return {"merged_groups": 0, "merged_tags": 0, "errors": 0}
    
    merged_groups = 0
    merged_tags = 0
    errors = 0
    
    for group_name, tag_group in duplicate_groups.items():
        try:
            canonical_tag = select_canonical_tag(tag_group)
            logger.info(f"Selected canonical tag for '{group_name}': {canonical_tag.name} ({canonical_tag.id})")
            
            # Merge all other tags into the canonical tag
            for tag in tag_group:
                if tag.id == canonical_tag.id:
                    continue
                
                logger.info(f"Merging tag {tag.name} ({tag.id}) into {canonical_tag.name} ({canonical_tag.id})")
                
                # Migrate all problem relationships
                if tag.problems:
                    for problem in tag.problems:
                        if canonical_tag not in problem.tags:
                            problem.tags.append(canonical_tag)
                    
                    # Flush to ensure relationships are updated
                    db.flush()
                
                # Delete the duplicate tag
                db.delete(tag)
                merged_tags += 1
            
            merged_groups += 1
            
        except Exception as e:
            logger.error(f"Error merging tags for group '{group_name}': {str(e)}")
            errors += 1
    
    # Commit changes
    if merged_tags > 0:
        try:
            db.commit()
            logger.info(f"Successfully merged {merged_tags} tags in {merged_groups} groups")
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing changes: {str(e)}")
            errors += 1
            merged_groups = 0
            merged_tags = 0
    
    return {
        "merged_groups": merged_groups,
        "merged_tags": merged_tags,
        "errors": errors
    }


def fix_eslint_tags(db):
    """Specifically target and fix ESLint tags."""
    # Find both variants of ESLint
    eslint_variants = db.query(Tag).filter(
        func.lower(Tag.name) == 'eslint'
    ).all()
    
    if len(eslint_variants) <= 1:
        logger.info("No duplicate ESLint tags found")
        return False
    
    logger.info(f"Found {len(eslint_variants)} ESLint variants: {', '.join(t.name for t in eslint_variants)}")
    
    # Prefer the properly capitalized "ESLint" or create it if needed
    canonical_eslint = next((t for t in eslint_variants if t.name == "ESLint"), None)
    
    if not canonical_eslint:
        # If no properly capitalized version exists, use the first one and rename it
        canonical_eslint = eslint_variants[0]
        canonical_eslint.name = "ESLint"
        logger.info(f"Renamed {canonical_eslint.name} to ESLint")
    
    # Merge all other variants into the canonical one
    merged = 0
    for tag in eslint_variants:
        if tag.id == canonical_eslint.id:
            continue
        
        logger.info(f"Merging tag {tag.name} ({tag.id}) into ESLint ({canonical_eslint.id})")
        
        # Migrate all problem relationships
        if tag.problems:
            for problem in tag.problems:
                if canonical_eslint not in problem.tags:
                    problem.tags.append(canonical_eslint)
        
        # Delete the duplicate tag
        db.delete(tag)
        merged += 1
    
    # Commit changes
    if merged > 0:
        try:
            db.commit()
            logger.info(f"Successfully merged {merged} ESLint tag variants")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error committing ESLint tag changes: {str(e)}")
    
    return False


if __name__ == "__main__":
    try:
        db = next(get_db())
        
        # First attempt to specifically fix ESLint tags
        eslint_fixed = fix_eslint_tags(db)
        
        # Then perform general duplicate tag merging
        results = merge_duplicate_tags(db)
        
        print("\nDuplicate Tag Merging Results:")
        print("=" * 50)
        if eslint_fixed:
            print("ESLint tags successfully consolidated")
        print(f"Tag groups merged: {results['merged_groups']}")
        print(f"Total tags merged: {results['merged_tags']}")
        print(f"Errors: {results['errors']}")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)
