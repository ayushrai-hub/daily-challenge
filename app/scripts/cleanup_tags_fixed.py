#!/usr/bin/env python3
"""
Tag Cleanup Script

Identifies and removes redundant tags from the database:
1. Test tags (test-child-*, test-parent-*)
2. Temporary placeholder tags (New-Tag-*)
3. Duplicate tags with different casing (JavaScript/javascript)
4. Empty tags or tags with no associations
5. Properly categorizes language tags

This helps maintain a clean and focused tag database.
"""

import sys
import os
import logging
import re
import argparse
import uuid
from typing import Dict, List, Set, Tuple
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import Session

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.core.config import settings
from app.db.session import get_db
from app.db.models.tag import Tag
from app.services.tag_mapper import get_tag_mapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SQL queries for identifying redundant tags
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
AND parent_tag_id IS NULL;
"""

DELETE_TAG = "DELETE FROM tags WHERE id = :tag_id;"

def identify_redundant_tags(conn) -> Dict[str, List[Dict]]:
    """Identify different categories of redundant tags using direct SQL queries"""
    redundant_tags = {
        "test_tags": [],
        "placeholder_tags": [],
        "temp_tags": [],
        "empty_tags": [],
        "orphaned_tags": []
    }
    
    # Execute queries for each category
    for category, query in [
        ("test_tags", SELECT_TEST_TAGS),
        ("placeholder_tags", SELECT_PLACEHOLDER_TAGS),
        ("temp_tags", SELECT_TEMP_TAGS),
        ("empty_tags", SELECT_EMPTY_TAGS),
        ("orphaned_tags", SELECT_ORPHANED_TAGS)
    ]:
        result = conn.execute(text(query))
        redundant_tags[category] = [dict(r) for r in result.fetchall()]
        
    return redundant_tags


def cleanup_redundant_tags(engine, dry_run: bool = True) -> Dict[str, int]:
    """Remove redundant tags from the database.
    
    Args:
        engine: SQLAlchemy engine for database connection
        dry_run: If True, only identifies tags without deleting them
        
    Returns:
        Dict with counts of identified/removed tags by category
    """
    conn = engine.connect()
    
    try:
        # Start transaction
        with conn.begin():
            # Identify redundant tags
            redundant_tags = identify_redundant_tags(conn)
            
            # Count tags by category
            counts = {category: len(tags) for category, tags in redundant_tags.items()}
            total = sum(counts.values())
            
            logger.info(f"Found {total} redundant tags:")
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
                        logger.info(f"  - {tag['name']} (ID: {tag['id']})")
                    if len(tags) > 10:
                        logger.info(f"  - ... and {len(tags) - 10} more")
                return counts
            
            # Delete tags in each category
            delete_count = 0
            for category, tags in redundant_tags.items():
                if not tags:
                    continue
                    
                logger.info(f"Deleting {len(tags)} tags from {category}...")
                for tag in tags:
                    # Delete the tag
                    conn.execute(text(DELETE_TAG), {"tag_id": tag["id"]})
                    delete_count += 1
                    
            logger.info(f"Deleted {delete_count} redundant tags")
            return counts
    except Exception as e:
        logger.error(f"Error during tag cleanup: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()


def fix_tag_categories(db: Session) -> Dict[str, int]:
    """Update tag categories to ensure proper classification.
    
    This ensures:
    1. All programming languages have tag_type='language'
    2. All programming languages are children of the 'Languages' category
    3. All parent category tags are featured
    
    Returns:
        Dict with counts of updated tags by category
    """
    stats = {
        "languages_updated": 0,
        "parents_featured": 0,
        "categories_updated": 0
    }
    
    # 1. Find or create the Languages parent category
    languages_category = db.query(Tag).filter(func.lower(Tag.name) == "languages").first()
    if not languages_category:
        languages_category = Tag(
            id=uuid.uuid4(),
            name="Languages",
            tag_type="domain",
            is_featured=True
        )
        db.add(languages_category)
        db.flush()
        logger.info(f"Created Languages category: {languages_category.id}")
    elif languages_category.tag_type != "domain":
        languages_category.tag_type = "domain"
        stats["categories_updated"] += 1
        logger.info(f"Updated Languages category to domain type: {languages_category.id}")
    
    # 2. Update common programming languages to have the correct tag_type
    language_names = [
        "JavaScript", "Python", "Java", "C++", "C#", "Go", "Rust", "Ruby", 
        "PHP", "Swift", "Kotlin", "TypeScript", "Scala", "Perl", "Haskell",
        "Clojure", "Erlang", "Elixir", "F#", "R", "MATLAB", "Dart"
    ]
    
    for lang_name in language_names:
        # Find by case-insensitive name match
        lang_tag = db.query(Tag).filter(func.lower(Tag.name) == lang_name.lower()).first()
        if not lang_tag:
            continue
            
        changes_made = False
        
        # Update tag_type if needed
        if lang_tag.tag_type != "language":
            lang_tag.tag_type = "language"
            changes_made = True
            stats["languages_updated"] += 1
        
        # Set parent to Languages category if not already set
        if not lang_tag.parent_tag_id or lang_tag.parent_tag_id != languages_category.id:
            lang_tag.parent_tag_id = languages_category.id
            changes_made = True
            stats["languages_updated"] += 1
            
        if changes_made:
            logger.info(f"Updated language tag: {lang_tag.name}")
    
    # 3. Make all parent category tags featured for better navigation
    parent_ids = db.query(Tag.parent_tag_id).distinct().filter(Tag.parent_tag_id.isnot(None))
    
    # Update all parent tags to be featured if not already
    for result in parent_ids:
        parent_id = result[0]
        parent_tag = db.query(Tag).filter(Tag.id == parent_id, Tag.is_featured == False).first()
        if parent_tag:
            parent_tag.is_featured = True
            stats["parents_featured"] += 1
            logger.info(f"Made parent tag featured: {parent_tag.name}")
    
    # 4. Update other known categories
    category_names = ["Data Structures", "Algorithms", "Design Patterns", "Frameworks", "Databases"]
    for cat_name in category_names:
        cat_tag = db.query(Tag).filter(func.lower(Tag.name) == cat_name.lower()).first()
        if cat_tag and cat_tag.tag_type not in ["domain", "topic"]:
            cat_tag.tag_type = "domain"
            stats["categories_updated"] += 1
            logger.info(f"Updated category tag type: {cat_tag.name}")
    
    # Commit changes
    db.commit()
    
    logger.info(f"Fixed tag categories: {stats}")
    return stats


def main():
    """Main entry point for the script"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Clean up redundant tags in the database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without making changes")
    parser.add_argument("--fix-categories", action="store_true", help="Fix tag categories and language tags")
    args = parser.parse_args()
    
    logger.info("Starting tag cleanup process")
    
    try:
        if args.fix_categories:
            # Fix tag categories using ORM
            db = next(get_db())
            try:
                stats = fix_tag_categories(db)
                logger.info(f"Category fix results: {stats}")
            except Exception as e:
                logger.error(f"Error fixing categories: {str(e)}")
                db.rollback()
                raise
            finally:
                db.close()
        else:
            # Get database connection from settings
            engine = create_engine(settings.DATABASE_URL)
            
            # Clean up redundant tags
            stats = cleanup_redundant_tags(engine, dry_run=args.dry_run)
            
            if not args.dry_run:
                logger.info("Running final duplicate check and merge...")
                # Get database session for ORM operations
                db = next(get_db())
                try:
                    # Get tag mapper service
                    tag_mapper = get_tag_mapper(db)
                    
                    # Run a final merge pass for any remaining duplicates
                    merge_stats = tag_mapper.merge_duplicate_tags()
                    logger.info(f"Duplicate merge results: {merge_stats}")
                finally:
                    db.close()
                
        logger.info("Tag cleanup process completed")
        
    except Exception as e:
        logger.error(f"Error during tag cleanup: {str(e)}")
        raise


if __name__ == "__main__":
    main()
