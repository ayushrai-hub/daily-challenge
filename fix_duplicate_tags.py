#!/usr/bin/env python3
"""
Fix Duplicate Tags Script

This script:
1. Identifies and merges duplicate tags (case-insensitive)
2. Normalizes all tag names according to standard conventions
3. Reassociates all problems with the correct normalized tags
4. Creates proper parent-child relationships for tags
"""

import sys
import os
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
import logging
from typing import Dict, List, Set, Tuple
import uuid

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.session import get_db
from app.db.models.tag import Tag, TagType
from app.db.models.problem import Problem
from app.db.models.problem_tag import ProblemTag
from app.api.routers.tags import normalize_tag_name, TECH_NAME_MAPPINGS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_duplicate_tags(db: Session) -> List[List[Tag]]:
    """
    Find duplicate tags based on case-insensitive name matching.
    
    Returns:
        List of lists, where each inner list contains duplicate tags
    """
    logger.info("Finding duplicate tags...")
    
    # Get all tags
    all_tags = db.query(Tag).all()
    
    # Create a dictionary to group tags by their lowercase name
    tags_by_lowercase = {}
    for tag in all_tags:
        key = tag.name.lower()
        if key not in tags_by_lowercase:
            tags_by_lowercase[key] = []
        tags_by_lowercase[key].append(tag)
    
    # Filter to only groups with more than one tag
    duplicates = [tags for key, tags in tags_by_lowercase.items() if len(tags) > 1]
    
    logger.info(f"Found {len(duplicates)} sets of duplicate tags")
    return duplicates

def get_primary_tag(tags: List[Tag]) -> Tag:
    """
    From a list of duplicate tags, select the primary one to keep.
    Prioritize:
    1. Tags with parent tags over those without
    2. Tags with properly capitalized names
    3. Tags used by more problems
    4. Tags with description over those without
    5. Oldest tag (lowest ID)
    """
    if not tags:
        raise ValueError("Empty tag list provided")
    
    # First priority: tags with parent tags
    tags_with_parents = [tag for tag in tags if tag.parent_tag_id]
    if tags_with_parents:
        tags = tags_with_parents
    
    # Second priority: properly capitalized names
    normalized_name = normalize_tag_name(tags[0].name)
    tags_with_proper_case = [tag for tag in tags if tag.name == normalized_name]
    if tags_with_proper_case:
        tags = tags_with_proper_case
    
    # Third priority: tags with more problem associations
    tags.sort(key=lambda tag: len(tag.problems) if hasattr(tag, 'problems') else 0, reverse=True)
    
    # Fourth priority: tags with descriptions
    tags_with_desc = [tag for tag in tags if tag.description]
    if tags_with_desc:
        return tags_with_desc[0]
    
    # Default: return the tag that should be used
    return tags[0]

def normalize_all_tag_names(db: Session) -> int:
    """
    Normalize all tag names according to standard conventions.
    
    Returns:
        int: Number of tags updated
    """
    logger.info("Normalizing all tag names...")
    
    # Get all tags
    all_tags = db.query(Tag).all()
    
    count = 0
    for tag in all_tags:
        normalized_name = normalize_tag_name(tag.name)
        if normalized_name != tag.name:
            logger.info(f"Normalizing tag: '{tag.name}' -> '{normalized_name}'")
            tag.name = normalized_name
            count += 1
    
    db.commit()
    logger.info(f"Normalized {count} tag names")
    return count

def merge_duplicate_tags(db: Session) -> Dict[str, int]:
    """
    Identify and merge duplicate tags.
    
    Returns:
        Dict with stats about operations performed
    """
    stats = {
        "duplicate_sets": 0,
        "tags_merged": 0,
        "problem_associations_updated": 0
    }
    
    # First normalize all tag names
    normalize_all_tag_names(db)
    
    # Find all duplicate tags
    duplicate_sets = find_duplicate_tags(db)
    stats["duplicate_sets"] = len(duplicate_sets)
    
    if not duplicate_sets:
        logger.info("No duplicate tags found after normalization.")
        return stats
    
    logger.info(f"Found {len(duplicate_sets)} sets of duplicate tags to merge")
    
    # Process each set of duplicates
    for duplicates in duplicate_sets:
        logger.info(f"Processing duplicate set: {[tag.name for tag in duplicates]}")
        
        # Select the primary tag to keep
        primary_tag = get_primary_tag(duplicates)
        logger.info(f"Selected primary tag: {primary_tag.name} (ID: {primary_tag.id})")
        
        # Ensure primary tag has the normalized name
        primary_tag.name = normalize_tag_name(primary_tag.name)
        
        # Merge the others into it
        for tag in duplicates:
            if tag.id == primary_tag.id:
                continue
                
            logger.info(f"Merging tag '{tag.name}' (ID: {tag.id}) into '{primary_tag.name}' (ID: {primary_tag.id})")
            
            # Update problem associations
            problem_tag_relations = db.query(ProblemTag).filter(ProblemTag.tag_id == tag.id).all()
            for pt in problem_tag_relations:
                # Check if there's already an association with the primary tag
                existing = db.query(ProblemTag).filter(
                    ProblemTag.problem_id == pt.problem_id,
                    ProblemTag.tag_id == primary_tag.id
                ).first()
                
                if not existing:
                    # Update to use the primary tag
                    pt.tag_id = primary_tag.id
                    stats["problem_associations_updated"] += 1
                else:
                    # Delete duplicate association
                    db.delete(pt)
            
            # Update any child tags to point to the primary tag
            child_tags = db.query(Tag).filter(Tag.parent_tag_id == tag.id).all()
            for child in child_tags:
                logger.info(f"Updating child tag '{child.name}' to point to primary parent")
                child.parent_tag_id = primary_tag.id
            
            # Delete the duplicate tag
            db.delete(tag)
            stats["tags_merged"] += 1
    
    db.commit()
    logger.info(f"Merged {stats['tags_merged']} duplicate tags")
    logger.info(f"Updated {stats['problem_associations_updated']} problem-tag associations")
    
    return stats

def fix_missing_parent_tags(db: Session) -> int:
    """
    Fix tags that should have a parent but don't (especially technology tags)
    
    Returns:
        int: Number of tags updated with parent relationships
    """
    logger.info("Fixing tags with missing parent relationships...")
    
    # Define parent categories to look for
    parent_categories = {
        "Languages": ["python", "javascript", "typescript", "java", "c++", "go", "rust"],
        "Algorithms": ["sorting", "searching", "dynamic programming", "recursion", "greedy"],
        "Data Structures": ["arrays", "linked lists", "trees", "graphs", "hash tables", "stacks", "queues"],
        "Code Quality": ["clean code", "testing", "refactoring", "design patterns", "code review"]
    }
    
    # Get all parent category tags
    parent_tags = {}
    for category_name in parent_categories.keys():
        category_tag = db.query(Tag).filter(func.lower(Tag.name) == category_name.lower()).first()
        if category_tag:
            parent_tags[category_name] = category_tag
        else:
            # Create category if it doesn't exist
            new_category = Tag(
                id=uuid.uuid4(),
                name=category_name,
                tag_type=TagType.category,
                is_featured=True
            )
            db.add(new_category)
            db.flush()
            parent_tags[category_name] = new_category
            logger.info(f"Created missing category tag: {category_name}")
    
    # Find tags that should have parents but don't
    orphan_tags = db.query(Tag).filter(Tag.parent_tag_id == None).all()
    
    count = 0
    for tag in orphan_tags:
        # Skip the parent categories themselves
        if tag.id in [parent.id for parent in parent_tags.values()]:
            continue
            
        # Check if this tag should belong to a category
        for category_name, tag_list in parent_categories.items():
            if tag.name.lower() in tag_list or any(t in tag.name.lower() for t in tag_list):
                parent = parent_tags[category_name]
                logger.info(f"Setting parent for orphan tag '{tag.name}' to '{parent.name}'")
                tag.parent_tag_id = parent.id
                count += 1
                break
    
    db.commit()
    logger.info(f"Fixed {count} tags with missing parent relationships")
    return count

def main():
    """Main entry point for the script"""
    logger.info("Starting tag cleanup process")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Merge duplicate tags
        merge_stats = merge_duplicate_tags(db)
        
        # Fix missing parent relationships
        parent_fixes = fix_missing_parent_tags(db)
        
        # Final normalization pass
        normalize_all_tag_names(db)
        
        logger.info("Tag cleanup completed successfully!")
        logger.info(f"Results: {merge_stats}, Parent relationships fixed: {parent_fixes}")
    except Exception as e:
        logger.error(f"Error during tag cleanup: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
