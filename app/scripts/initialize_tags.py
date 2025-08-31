#!/usr/bin/env python3
"""
Tag Initialization Script for Daily Challenge Platform

This script is responsible for ensuring that the database has the basic
tag structure required for the platform to function correctly. It will:

1. Create the main tag categories if they don't exist
2. Create default tags under each category if needed
3. Log any changes made to the database

This provides a proper production-ready solution for tag initialization.
"""

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models.tag import Tag, TagType
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_tags(db: Session, force_update=False):
    """
    Initialize the tag structure in the database.
    
    Args:
        db: Database session
        force_update: If True, will add missing tags even if some already exist
    
    Returns:
        dict: Stats about operations performed
    """
    stats = {
        "categories_created": 0,
        "tags_created": 0,
        "already_initialized": False
    }
    
    # Only initialize if there are no tags or if force_update is True
    existing_tag_count = db.query(Tag).count()
    
    if existing_tag_count > 0 and not force_update:
        logger.info(f"Database already has {existing_tag_count} tags. Initialization skipped.")
        stats["already_initialized"] = True
        return stats
    
    logger.info(f"Found {existing_tag_count} existing tags. Initializing missing tag structure.")
    
    # Define our core categories
    core_categories = [
        {"name": "Languages", "type": TagType.category, "featured": True},
        {"name": "Algorithms", "type": TagType.category, "featured": True},
        {"name": "Data Structures", "type": TagType.category, "featured": True},
        {"name": "Code Quality", "type": TagType.category, "featured": True}
    ]
    
    # Create or get the category tags
    category_map = {}
    for cat in core_categories:
        # Check if this category already exists
        existing = db.query(Tag).filter(Tag.name == cat["name"]).first()
        
        if existing:
            logger.info(f"Category '{cat['name']}' already exists, using existing.")
            category_map[cat["name"]] = existing
        else:
            # Create new category tag
            new_category = Tag(
                id=uuid.uuid4(),
                name=cat["name"],
                tag_type=cat["type"],
                is_featured=cat["featured"]
            )
            db.add(new_category)
            db.flush()  # Flush to get the ID
            category_map[cat["name"]] = new_category
            stats["categories_created"] += 1
            logger.info(f"Created category: {cat['name']}")
    
    # Define the tags for each category
    category_tags = {
        "Languages": [
            {"name": "Python", "type": TagType.technology},
            {"name": "JavaScript", "type": TagType.technology},
            {"name": "TypeScript", "type": TagType.technology},
            {"name": "Java", "type": TagType.technology},
            {"name": "C++", "type": TagType.technology},
            {"name": "Go", "type": TagType.technology},
            {"name": "Rust", "type": TagType.technology}
        ],
        "Algorithms": [
            {"name": "Sorting", "type": TagType.concept},
            {"name": "Searching", "type": TagType.concept},
            {"name": "Graph Algorithms", "type": TagType.concept},
            {"name": "Dynamic Programming", "type": TagType.concept},
            {"name": "Divide and Conquer", "type": TagType.concept}
        ],
        "Data Structures": [
            {"name": "Arrays", "type": TagType.concept},
            {"name": "Linked Lists", "type": TagType.concept},
            {"name": "Trees", "type": TagType.concept},
            {"name": "Graphs", "type": TagType.concept},
            {"name": "Hash Tables", "type": TagType.concept},
            {"name": "Stacks", "type": TagType.concept},
            {"name": "Queues", "type": TagType.concept}
        ],
        "Code Quality": [
            {"name": "Clean Code", "type": TagType.concept},
            {"name": "Refactoring", "type": TagType.concept},
            {"name": "Testing", "type": TagType.concept},
            {"name": "Design Patterns", "type": TagType.concept},
            {"name": "Code Review", "type": TagType.concept}
        ]
    }
    
    # Create tags under each category
    for category_name, tags in category_tags.items():
        category = category_map.get(category_name)
        if not category:
            logger.warning(f"Category {category_name} not found in map, skipping its tags")
            continue
            
        for tag_data in tags:
            # Check if this tag already exists
            existing = db.query(Tag).filter(
                Tag.name == tag_data["name"],
                Tag.parent_tag_id == category.id
            ).first()
            
            if existing:
                logger.info(f"Tag '{tag_data['name']}' already exists under '{category_name}', skipping.")
                continue
                
            # Create the new tag
            new_tag = Tag(
                id=uuid.uuid4(),
                name=tag_data["name"],
                tag_type=tag_data["type"],
                parent_tag_id=category.id
            )
            db.add(new_tag)
            stats["tags_created"] += 1
            logger.info(f"Created tag: {tag_data['name']} under {category_name}")
    
    # Commit all changes
    db.commit()
    logger.info(f"Tag initialization complete. Created {stats['categories_created']} categories and {stats['tags_created']} tags.")
    return stats

def main():
    """Main entry point for the script when run directly"""
    logger.info("Starting tag initialization process")
    # Get database session
    db = next(get_db())
    try:
        stats = initialize_tags(db)
        if stats["already_initialized"]:
            logger.info("Tags already initialized. Use --force to add missing tags.")
        else:
            logger.info(f"Results: {stats}")
    except Exception as e:
        logger.error(f"Error initializing tags: {str(e)}")
        raise
    finally:
        db.close()
    logger.info("Tag initialization process complete")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Initialize tag structure in database')
    parser.add_argument('--force', action='store_true', help='Force update even if tags exist')
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    try:
        stats = initialize_tags(db, force_update=args.force)
        print(f"Tag initialization {'completed' if not stats['already_initialized'] else 'skipped (already initialized)'}.")
        print(f"Stats: {stats}")
    finally:
        db.close()
