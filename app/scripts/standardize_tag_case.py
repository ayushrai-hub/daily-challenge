"""
Script to standardize tag case in the database.

This script:
1. Uses the TagNormalizer to determine the proper case for each tag
2. Updates existing tags to use standardized capitalization
3. Maintains all relationships while updating tag names
"""
import sys
import os
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

from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.services.tag_mapper import get_tag_mapper
from app.core.logging import get_logger

logger = get_logger()

def standardize_tag_case():
    """Update tag names in the database to use standardized capitalization."""
    # Get DB session
    db = next(get_db())
    
    # Initialize repositories and services
    tag_repo = TagRepository(db)
    normalizer = TagNormalizer(tag_repo)
    tag_mapper = get_tag_mapper(db)
    
    # Get all tags
    all_tags = db.query(Tag).all()
    logger.info(f"Found {len(all_tags)} tags in the database")
    
    # Track changes
    changes = []
    no_changes = []
    errors = []
    merge_operations = []
    
    # First collect all the normalized names to detect potential conflicts
    tag_name_to_normalized = {}
    normalized_to_tags = {}
    
    for tag in all_tags:
        original_name = tag.name
        
        # Get normalized version of the tag name
        normalized_names = normalizer.normalize_tag_names([original_name])
        if not normalized_names:
            logger.warning(f"Could not normalize tag '{original_name}', skipping")
            no_changes.append(original_name)
            continue
            
        normalized_name = normalized_names[0]
        tag_name_to_normalized[original_name] = normalized_name
        
        # Group tags by their normalized name to detect duplicates
        if normalized_name not in normalized_to_tags:
            normalized_to_tags[normalized_name] = []
        normalized_to_tags[normalized_name].append(tag)
    
    # Process each normalization group
    for normalized_name, tags in normalized_to_tags.items():
        if len(tags) == 1:
            # Single tag case - just update if needed
            tag = tags[0]
            if tag.name != normalized_name:
                try:
                    # Check if another tag with the normalized name already exists
                    existing_tag = tag_repo.get_by_name(normalized_name)
                    if existing_tag and existing_tag.id != tag.id:
                        # Need to merge instead of rename
                        logger.info(f"Will merge '{tag.name}' into existing tag '{normalized_name}'")
                        merge_operations.append((tag.id, existing_tag.id))
                    else:
                        # Safe to rename
                        original_name = tag.name
                        tag.name = normalized_name
                        logger.info(f"Updated tag '{original_name}' to '{normalized_name}'")
                        changes.append((original_name, normalized_name))
                except Exception as e:
                    logger.error(f"Error processing tag '{tag.name}': {str(e)}")
                    errors.append(tag.name)
        else:
            # Multiple tags with same normalized form - need to merge
            # Sort to find the best canonical tag (one that already has the proper name)
            tags.sort(key=lambda t: 1 if t.name == normalized_name else 0, reverse=True)
            
            canonical_tag = tags[0]
            logger.info(f"Selected canonical tag '{canonical_tag.name}' for normalized name '{normalized_name}'")
            
            # If canonical tag doesn't have the normalized name yet, update it
            if canonical_tag.name != normalized_name:
                original_name = canonical_tag.name
                canonical_tag.name = normalized_name
                logger.info(f"Updated canonical tag from '{original_name}' to '{normalized_name}'")
                changes.append((original_name, normalized_name))
            
            # Schedule all other tags for merging
            for tag in tags[1:]:
                logger.info(f"Will merge '{tag.name}' into canonical tag '{canonical_tag.name}'")
                merge_operations.append((tag.id, canonical_tag.id))
    
    # Commit name changes first
    try:
        if changes:
            db.commit()
            logger.info(f"Successfully updated {len(changes)} tag names")
        else:
            logger.info("No tag name updates needed")
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing tag updates: {str(e)}")
        raise
    
    # Now perform merges
    merge_count = 0
    for source_id, target_id in merge_operations:
        try:
            tag_mapper.merge_tag(source_id, target_id)
            merge_count += 1
        except Exception as e:
            logger.error(f"Error merging tag {source_id} into {target_id}: {str(e)}")
            errors.append(f"Merge {source_id} -> {target_id}")
    
    # Commit the merges
    try:
        if merge_count > 0:
            db.commit()
            logger.info(f"Successfully merged {merge_count} tags")
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing tag merges: {str(e)}")
        raise
    
    return {
        "total_tags": len(all_tags),
        "changes": changes,
        "no_changes": no_changes,
        "errors": errors
    }

if __name__ == "__main__":
    try:
        results = standardize_tag_case()
        
        print("\nTag Case Standardization Results:")
        print("=" * 50)
        print(f"Total tags processed: {results['total_tags']}")
        print(f"Tags updated: {len(results['changes'])}")
        print(f"Tags already standardized: {len(results['no_changes'])}")
        print(f"Errors: {len(results['errors'])}")
        
        if results['changes']:
            print("\nTag name changes:")
            for original, updated in results['changes']:
                print(f"  '{original}' → '{updated}'")
                
        if results['errors']:
            print("\nTags with errors:")
            for tag_name in results['errors']:
                print(f"  '{tag_name}'")
                
        print("=" * 50)
    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        print(f"\nError: {str(e)}")
        sys.exit(1)
