#!/usr/bin/env python3
"""
Script to find and merge duplicate tags in the database.

This script identifies tags with case-insensitive name matches, 
normalizes them, and updates all references to use a single canonical tag.

Usage:
    python scripts/clean_duplicate_tags.py [--dry-run]

Options:
    --dry-run    Run without making any changes to the database
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from sqlalchemy import text, func, or_, and_
from sqlalchemy.orm import aliased

# Add the project root to sys.path to enable imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"tag_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tag_cleanup")

# Import app-specific modules after setting up path
from app.db.database import get_db
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.association_tables import problem_tags
from app.db.models.tag_normalization import TagNormalization
from app.repositories.tag import TagRepository
from app.core.config import init_settings

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Find and merge duplicate tags.')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without actually changing the database')
    return parser.parse_args()

def find_duplicate_tags(db):
    """Find tags with the same case-insensitive name."""
    # Use a CTE (Common Table Expression) to find duplicates
    query = text("""
        WITH normalized_tags AS (
            SELECT id, name, LOWER(name) as lower_name
            FROM tags
        ),
        duplicate_groups AS (
            SELECT lower_name, array_agg(id) as tag_ids, array_agg(name) as tag_names
            FROM normalized_tags
            GROUP BY lower_name
            HAVING COUNT(*) > 1
        )
        SELECT * FROM duplicate_groups
        ORDER BY lower_name;
    """)
    
    result = db.execute(query)
    duplicates = []
    
    for row in result:
        duplicates.append({
            "lower_name": row.lower_name,
            "tag_ids": row.tag_ids,
            "tag_names": row.tag_names
        })
    
    logger.info(f"Found {len(duplicates)} tag groups with duplicates")
    return duplicates

def select_canonical_tag(db, tag_ids, tag_names):
    """Select the best tag to keep from a group of duplicates."""
    # Rules for selecting canonical tag:
    # 1. Prefer names with proper casing (e.g., "JavaScript" over "javascript")
    # 2. Prefer tags with more problem associations
    # 3. Prefer tags with more complete metadata (description)
    # 4. Prefer older tags (lower ID)
    
    tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
    
    # First, try to find a properly cased version (has both upper and lower case)
    properly_cased = [tag for tag in tags if not tag.name.islower() and not tag.name.isupper()]
    if properly_cased:
        # If multiple properly cased, get the one with most references
        problem_counts = {}
        for tag in properly_cased:
            # Count problems using the association table
            count = db.query(problem_tags).filter(problem_tags.c.tag_id == tag.id).count()
            problem_counts[tag.id] = count
            
        canonical_tag = max(properly_cased, key=lambda tag: (
            problem_counts.get(tag.id, 0),  # Most problems
            1 if tag.description else 0,    # Has description
            str(tag.id)                     # Sort by ID string (not ideal but safe)
        ))
        return canonical_tag
    
    # If no properly cased, get the one with most references
    problem_counts = {}
    for tag in tags:
        # Count problems using the association table
        count = db.query(problem_tags).filter(problem_tags.c.tag_id == tag.id).count()
        problem_counts[tag.id] = count
    
    canonical_tag = max(tags, key=lambda tag: (
        problem_counts.get(tag.id, 0),  # Most problems
        1 if tag.description else 0,    # Has description
        str(tag.id)                     # Sort by ID string (not ideal but safe)
    ))
    
    return canonical_tag

def merge_tags(db, canonical_tag, duplicate_tag_ids, dry_run=False):
    """Merge duplicate tags into the canonical tag."""
    if dry_run:
        logger.info(f"DRY RUN: Would merge tags {duplicate_tag_ids} into {canonical_tag.id} ({canonical_tag.name})")
        return
    
    duplicate_tag_ids = [id for id in duplicate_tag_ids if id != canonical_tag.id]
    
    # Update problem_tags association table using direct SQL
    # First, find all problem-tag associations for duplicate tags
    from sqlalchemy import text
    problem_tag_pairs = []
    for tag_id in duplicate_tag_ids:
        # Get all problem_ids associated with this tag
        result = db.execute(
            text(f"SELECT problem_id FROM problem_tags WHERE tag_id = '{tag_id}'::uuid")
        )
        for row in result:
            problem_tag_pairs.append((row[0], tag_id))
    
    # For each problem-tag pair, check if it already exists with canonical tag
    # If not, create it; if yes, skip it
    created_count = 0
    for problem_id, tag_id in problem_tag_pairs:
        # Check if this problem is already associated with the canonical tag
        exists = db.execute(
            text(f"SELECT 1 FROM problem_tags WHERE problem_id = '{problem_id}'::uuid AND tag_id = '{canonical_tag.id}'::uuid")
        ).fetchone() is not None
        
        if not exists:
            # Create new association with canonical tag
            db.execute(
                text(f"INSERT INTO problem_tags (problem_id, tag_id) VALUES ('{problem_id}'::uuid, '{canonical_tag.id}'::uuid)")
            )
            created_count += 1
    
    # Now delete all associations with duplicate tags
    for tag_id in duplicate_tag_ids:
        deleted = db.execute(
            text(f"DELETE FROM problem_tags WHERE tag_id = '{tag_id}'::uuid")
        )
    
    logger.info(f"Created {created_count} new problem_tag entries for canonical tag")
    
    # Handle tag hierarchies - parent relationships
    # First, get all affected relationships
    parent_hierarchies = db.query(TagHierarchy).filter(
        TagHierarchy.child_tag_id.in_(duplicate_tag_ids)
    ).all()
    
    # Create new parent relationships for the canonical tag
    parent_count = 0
    for hierarchy in parent_hierarchies:
        # Check if this relationship already exists for the canonical tag
        exists = db.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == hierarchy.parent_tag_id,
            TagHierarchy.child_tag_id == canonical_tag.id
        ).first() is not None
        
        if not exists:
            new_hierarchy = TagHierarchy(
                parent_tag_id=hierarchy.parent_tag_id,
                child_tag_id=canonical_tag.id
            )
            db.add(new_hierarchy)
            parent_count += 1
    
    logger.info(f"Created {parent_count} new parent relationships for canonical tag")
    
    # Handle tag hierarchies - child relationships 
    child_hierarchies = db.query(TagHierarchy).filter(
        TagHierarchy.parent_tag_id.in_(duplicate_tag_ids)
    ).all()
    
    # Create new child relationships for the canonical tag
    child_count = 0
    for hierarchy in child_hierarchies:
        # Check if this relationship already exists for the canonical tag
        exists = db.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == canonical_tag.id,
            TagHierarchy.child_tag_id == hierarchy.child_tag_id
        ).first() is not None
        
        if not exists:
            new_hierarchy = TagHierarchy(
                parent_tag_id=canonical_tag.id,
                child_tag_id=hierarchy.child_tag_id
            )
            db.add(new_hierarchy)
            child_count += 1
    
    logger.info(f"Created {child_count} new child relationships for canonical tag")
    
    # Update tag_normalizations that point to duplicates
    norm_updated = db.query(TagNormalization).filter(
        TagNormalization.approved_tag_id.in_(duplicate_tag_ids)
    ).update({
        "approved_tag_id": canonical_tag.id
    }, synchronize_session=False)
    
    logger.info(f"Updated {norm_updated} tag_normalization entries")
    
    # Delete old tag hierarchy entries
    hierarchy_deleted = db.query(TagHierarchy).filter(
        or_(
            TagHierarchy.parent_tag_id.in_(duplicate_tag_ids),
            TagHierarchy.child_tag_id.in_(duplicate_tag_ids)
        )
    ).delete(synchronize_session=False)
    
    logger.info(f"Deleted {hierarchy_deleted} tag hierarchy entries")
    
    # Finally, delete the duplicate tags
    for tag_id in duplicate_tag_ids:
        # Special trigger for PostgreSQL to avoid foreign key issues
        # Properly quote the UUID to avoid SQL syntax errors
        db.execute(text(f"DELETE FROM tags WHERE id = '{tag_id}'::uuid"))
    
    logger.info(f"Deleted {len(duplicate_tag_ids)} duplicate tags")
    
    # Commit changes
    db.commit()

def main():
    """Main script execution."""
    args = parse_args()
    init_settings()
    
    logger.info(f"Starting tag cleanup script with dry_run={args.dry_run}")
    
    # Get database session
    db = next(get_db())
    try:
        # Find and process duplicate tags
        duplicate_groups = find_duplicate_tags(db)
        
        if not duplicate_groups:
            logger.info("No duplicate tags found. Database is clean.")
            return
        
        total_merged = 0
        for group in duplicate_groups:
            logger.info(f"Processing duplicate group: {group['tag_names']} ({group['tag_ids']})")
            
            # Select the canonical tag to keep
            canonical_tag = select_canonical_tag(db, group['tag_ids'], group['tag_names'])
            logger.info(f"Selected canonical tag: {canonical_tag.name} (ID: {canonical_tag.id})")
            
            # Merge all others into the canonical tag
            merge_tags(db, canonical_tag, group['tag_ids'], args.dry_run)
            
            total_merged += len(group['tag_ids']) - 1
        
        logger.info(f"Cleanup completed. Merged {total_merged} duplicate tags{'(dry run)' if args.dry_run else ''}.")
        
    except Exception as e:
        logger.error(f"Error during tag cleanup: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
