#!/usr/bin/env python3
"""
Fix Specific Tag Duplicates Script

This script specifically fixes the identified duplicate tags:
1. 'javascript'/'JavaScript' 
2. 'languages'/'Languages'

It ensures proper capitalization and maintains all relationships.
"""

import sys
import os
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
import logging
from typing import Dict, List, Tuple
import uuid

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.session import get_db
from app.db.models.tag import Tag
from app.services.tag_mapper import get_tag_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the specific tags we want to fix
TAG_FIXES = [
    {
        "lowercase": "javascript",
        "proper_case": "JavaScript",
        "parent_category": "Languages"
    },
    {
        "lowercase": "languages",
        "proper_case": "Languages",
        "parent_category": None  # This is a top-level category
    }
]

def fix_specific_duplicate_tags(db: Session) -> Dict[str, int]:
    """
    Fix the specific case-sensitive duplicate tags we identified.
    
    Returns:
        Dict with stats about operations performed
    """
    # Get the tag_mapper service
    tag_mapper = get_tag_mapper(db)
    
    # Stats to collect
    stats = {
        "merged_tags": 0,
        "parent_relationships_fixed": 0
    }
    
    # Process each tag fix
    for fix in TAG_FIXES:
        logger.info(f"Processing fix for {fix['lowercase']}/{fix['proper_case']}")
        
        # Get all variations of this tag (case-insensitive)
        tags = db.query(Tag).filter(func.lower(Tag.name) == fix['lowercase'].lower()).all()
        
        if len(tags) <= 0:
            logger.info(f"No tags found for {fix['lowercase']}")
            continue
            
        if len(tags) == 1:
            # Only one tag exists, just ensure proper capitalization
            tag = tags[0]
            if tag.name != fix['proper_case']:
                logger.info(f"Updating tag capitalization: {tag.name} -> {fix['proper_case']}")
                tag.name = fix['proper_case']
            continue
            
        logger.info(f"Found {len(tags)} variations of {fix['lowercase']}")
        
        # Sort tags by proper capitalization and number of problems
        # Keep JavaScript (proper case) or the one with most problems
        tags.sort(key=lambda t: (
            t.name != fix['proper_case'],  # Prefer the proper case
            -len(t.problems)               # Then prefer the one with more problems
        ))
        
        # The first tag is the one to keep
        target_tag = tags[0]
        
        # If target tag doesn't have proper capitalization, fix it
        if target_tag.name != fix['proper_case']:
            logger.info(f"Updating primary tag capitalization: {target_tag.name} -> {fix['proper_case']}")
            target_tag.name = fix['proper_case']
            
        # Merge all other duplicates into the target
        for source_tag in tags[1:]:
            logger.info(f"Merging {source_tag.name} ({source_tag.id}) into {target_tag.name} ({target_tag.id})")
            tag_mapper.merge_tag(source_tag.id, target_tag.id)
            stats["merged_tags"] += 1
        
        # If this tag needs a parent category, set it
        if fix["parent_category"]:
            # Find parent category tag
            parent_tag = db.query(Tag).filter(func.lower(Tag.name) == fix["parent_category"].lower()).first()
            
            if parent_tag and not target_tag.parent_tag_id:
                logger.info(f"Setting parent for {target_tag.name} to {parent_tag.name}")
                target_tag.parent_tag_id = parent_tag.id
                stats["parent_relationships_fixed"] += 1
                
    # Commit all changes
    db.commit()
    
    return stats

def fix_language_hierarchy(db: Session):
    """
    Ensure JavaScript is a child of Languages.
    """
    # Find Languages tag
    languages_tag = db.query(Tag).filter(func.lower(Tag.name) == "languages").first()
    if not languages_tag:
        logger.error("Languages tag not found!")
        return
        
    # Find JavaScript tag 
    javascript_tag = db.query(Tag).filter(func.lower(Tag.name) == "javascript").first()
    if not javascript_tag:
        logger.error("JavaScript tag not found!")
        return
    
    # Set up the parent-child relationship
    if not javascript_tag.parent_tag_id:
        javascript_tag.parent_tag_id = languages_tag.id
        logger.info(f"Set {javascript_tag.name} as child of {languages_tag.name}")
        db.commit()
    elif javascript_tag.parent_tag_id != languages_tag.id:
        previous_parent = db.query(Tag).filter(Tag.id == javascript_tag.parent_tag_id).first()
        prev_name = previous_parent.name if previous_parent else "Unknown"
        logger.info(f"Changed parent of {javascript_tag.name} from {prev_name} to {languages_tag.name}")
        javascript_tag.parent_tag_id = languages_tag.id
        db.commit()
    else:
        logger.info(f"{javascript_tag.name} is already a child of {languages_tag.name}")

def main():
    """Main entry point for the script"""
    logger.info("Starting specific tag fixes")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Fix duplicate tags
        stats = fix_specific_duplicate_tags(db)
        
        # Ensure JavaScript is a child of Languages
        fix_language_hierarchy(db)
        
        logger.info("Tag fixes completed successfully!")
        logger.info(f"Results: {stats}")
    except Exception as e:
        logger.error(f"Error during tag fixes: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
