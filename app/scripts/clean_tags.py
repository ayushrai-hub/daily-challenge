#!/usr/bin/env python3
"""
Tag Cleanup Script

Identifies and removes redundant tags from the database:
1. Test tags (test-child-*, test-parent-*)
2. Temporary placeholder tags (New-Tag-*)
3. Duplicate tags with different casing (JavaScript/javascript)
4. Empty tags or tags with no associations

This helps maintain a clean and focused tag database.
"""

import sys
import os
import logging
import re
import argparse
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQL queries for identifying and cleaning up redundant tags
SELECT_TEST_TAGS = """
SELECT id, name, description 
FROM tags 
WHERE name LIKE 'test-%' 
AND id NOT IN (SELECT tag_id FROM problem_tags);
"""

SELECT_PLACEHOLDER_TAGS = """
SELECT id, name, description 
FROM tags 
WHERE name LIKE 'New-Tag-%' 
AND id NOT IN (SELECT tag_id FROM problem_tags);
"""

SELECT_TEMP_TAGS = """
SELECT id, name, description 
FROM tags 
WHERE (name LIKE 'Temp%' OR name LIKE 'temp%' OR name LIKE '%_temp' OR name LIKE '%_TEMP') 
AND id NOT IN (SELECT tag_id FROM problem_tags);
"""

SELECT_EMPTY_TAGS = """
SELECT id, name, description 
FROM tags 
WHERE (name = '' OR name IS NULL) 
AND id NOT IN (SELECT tag_id FROM problem_tags);
"""

SELECT_ORPHANED_TAGS = """
SELECT id, name, description 
FROM tags 
WHERE id NOT IN (SELECT tag_id FROM problem_tags) 
AND parent_tag_id IS NULL 
AND id NOT IN (SELECT id FROM tags WHERE parent_tag_id IS NOT NULL);
"""

# SQL query to find duplicate tags with different casing
SELECT_CASE_DUPLICATES = """
SELECT t1.id, t1.name, t1.description, 
       ARRAY_AGG(t2.id) AS duplicate_ids,
       ARRAY_AGG(t2.name) AS duplicate_names
FROM tags t1
JOIN tags t2 ON LOWER(t1.name) = LOWER(t2.name) AND t1.id != t2.id
GROUP BY t1.id, t1.name, t1.description;
"""

DELETE_TAG = "DELETE FROM tags WHERE id = :tag_id;"

def identify_redundant_tags(conn) -> Dict[str, List[Dict]]:
    """Identify different categories of redundant tags using direct SQL queries"""
    redundant_tags = {
        "test_tags": [],
        "placeholder_tags": [],
        "temp_tags": [],
        "empty_tags": [],
        "orphaned_tags": [],
        "case_duplicates": []
    }
    
    # Execute queries for each category
    for category, query in [
        ("test_tags", SELECT_TEST_TAGS),
        ("placeholder_tags", SELECT_PLACEHOLDER_TAGS),
        ("temp_tags", SELECT_TEMP_TAGS),
        ("empty_tags", SELECT_EMPTY_TAGS),
        ("orphaned_tags", SELECT_ORPHANED_TAGS),
        ("case_duplicates", SELECT_CASE_DUPLICATES)
    ]:
        result = conn.execute(text(query))
        redundant_tags[category] = [row._mapping for row in result.fetchall()]
        
    return redundant_tags

# SQL for child tag cleanup and deletion
SET_NULL_PARENT = "UPDATE tags SET parent_tag_id = NULL WHERE parent_tag_id = :tag_id;"
CHILD_TAGS_FOR_PARENT = "SELECT id FROM tags WHERE parent_tag_id = :tag_id;"

def has_child_tags(conn, tag_id):
    """Check if a tag has child tags"""
    result = conn.execute(text(CHILD_TAGS_FOR_PARENT), {"tag_id": tag_id})
    return result.fetchone() is not None

def cleanup_redundant_tags(engine, dry_run: bool = True, only_test_tags: bool = True) -> Dict[str, int]:
    """Remove redundant tags from the database.
    
    Args:
        engine: SQLAlchemy engine for database connection
        dry_run: If True, only identifies tags without deleting them
        only_test_tags: If True, only remove test tags and placeholder tags (safe cleanup)
        
    Returns:
        Dict with counts of identified/removed tags by category
    """
    conn = engine.connect()
    
    try:
        # Start transaction
        with conn.begin():
            # Identify redundant tags
            redundant_tags = identify_redundant_tags(conn)
            
            # Filter categories if only_test_tags is True
            if only_test_tags:
                logger.info("SAFE MODE: Only removing test and placeholder tags")
                # Keep only test and placeholder tags
                categories_to_keep = ["test_tags", "placeholder_tags"]
                redundant_tags = {k: v for k, v in redundant_tags.items() if k in categories_to_keep}
            
            # Count tags by category
            counts = {category: len(tags) for category, tags in redundant_tags.items()}
            total = sum(counts.values())
            
            logger.info(f"Found {total} redundant tags to process:")
            for category, count in counts.items():
                logger.info(f"  - {category}: {count}")
            
            if dry_run:
                logger.info("DRY RUN: No changes will be made")
                # Print some examples of what would be removed
                for category, tags in redundant_tags.items():
                    if not tags:
                        continue
                        
                    logger.info(f"\n{category.upper()}:")
                    for tag in tags[:10]:  # Show first 10 tags in each category
                        if category == "case_duplicates":
                            logger.info(f"  - {tag['name']} (ID: {tag['id']}) has duplicates: {tag['duplicate_names']}")
                        else:
                            logger.info(f"  - {tag['name']} (ID: {tag['id']})")
                    if len(tags) > 10:
                        logger.info(f"  - ... and {len(tags) - 10} more")
                        
                # Rollback transaction in dry-run mode
                return counts
            
            # Delete redundant tags if not dry-run
            deleted_counts = {}
            
            # Process categories in a specific order to handle parent-child relationships
            for category in redundant_tags.keys():
                if category == "case_duplicates":
                    continue  # Skip case duplicates for now
                
                tags = redundant_tags[category]
                if not tags:
                    deleted_counts[category] = 0
                    continue
                    
                logger.info(f"Processing {len(tags)} {category}...")
                deleted = 0
                
                for tag in tags:
                    tag_id = tag['id']
                    
                    # Check if this tag has child tags
                    if has_child_tags(conn, tag_id):
                        logger.info(f"Tag '{tag['name']}' (ID: {tag_id}) has child tags. Setting their parent to NULL first.")
                        conn.execute(text(SET_NULL_PARENT), {"tag_id": tag_id})
                    
                    # Now delete the tag
                    try:
                        conn.execute(text(DELETE_TAG), {"tag_id": tag_id})
                        deleted += 1
                        logger.debug(f"Deleted tag: {tag['name']} (ID: {tag_id})")
                    except Exception as e:
                        logger.warning(f"Failed to delete tag '{tag['name']}' (ID: {tag_id}): {str(e)}")
                
                deleted_counts[category] = deleted
                logger.info(f"Successfully deleted {deleted} out of {len(tags)} {category}")
            
            # Special handling for case duplicate tags
            if "case_duplicates" in redundant_tags and redundant_tags["case_duplicates"] and not only_test_tags:
                logger.info(f"Merging {len(redundant_tags['case_duplicates'])} case-insensitive duplicate tags...")
                # TODO: Implement merging logic here if needed
                # For now, we're just reporting duplicates
                
            total_deleted = sum(deleted_counts.values())
            logger.info(f"Cleanup complete. Deleted {total_deleted} redundant tags")
            return deleted_counts
            
    finally:
        conn.close()

def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Clean up redundant tags in the database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be removed without making changes')
    parser.add_argument('--execute', action='store_true', help='Actually delete redundant tags')
    args = parser.parse_args()
    
    # Default to dry run unless --execute is specified
    dry_run = not args.execute
    
    logger.info("Starting tag cleanup process")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        # Clean up redundant tags
        counts = cleanup_redundant_tags(engine, dry_run=dry_run)
        
        if not dry_run:
            logger.info("Tag cleanup completed successfully!")
            logger.info(f"Deleted tags: {counts}")
        else:
            logger.info("\nTo execute the cleanup, run with --execute flag:")
            logger.info("python -m app.scripts.clean_tags --execute")
        
    except Exception as e:
        logger.error(f"Error during tag cleanup: {str(e)}")
        raise

if __name__ == "__main__":
    main()
