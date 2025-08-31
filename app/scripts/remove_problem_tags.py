#!/usr/bin/env python
"""
Script to remove problematic tags from the database and allow them to be recreated.
This addresses session binding issues with specific tags in the content pipeline.
"""
import sys
import os
from pathlib import Path

# Add the parent directory to the sys.path to allow imports from app
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.db.session import get_sync_db
from app.repositories.tag import TagRepository
from app.core.logging import get_logger

logger = get_logger()

def remove_problem_tags():
    """Remove tags that are causing session binding issues in the content pipeline."""
    problem_tags = ["python", "fastapi"]
    
    db = next(get_sync_db())
    tag_repo = TagRepository(db)
    
    # First, check if tag_normalizations table exists
    try:
        db.execute(text("SELECT 1 FROM tag_normalizationss LIMIT 1"))
        tag_normalizations_exists = True
        logger.info("tag_normalizations table exists")
    except Exception:
        tag_normalizations_exists = False
        logger.info("tag_normalizations table does not exist")
    
    for tag_name in problem_tags:
        try:
            logger.info(f"Looking for tag '{tag_name}'...")
            # Find the tag using properly declared text SQL
            query = text(f"SELECT id, name FROM tags WHERE LOWER(name) = LOWER(:tag_name)")
            tag = db.execute(query, {"tag_name": tag_name}).first()
            
            if tag:
                # First remove associations
                logger.info(f"Removing tag '{tag_name}' (ID: {tag.id}) associations...")
                
                # Use properly declared text SQL with parameters
                db.execute(text("DELETE FROM problem_tags WHERE tag_id = :tag_id"), {"tag_id": tag.id})
                db.execute(text("DELETE FROM user_tags WHERE tag_id = :tag_id"), {"tag_id": tag.id})
                
                # Also check if there are any tag hierarchy relationships
                try:
                    hierarchy_query = text("DELETE FROM tag_hierarchy WHERE parent_tag_id = :tag_id OR child_tag_id = :tag_id")
                    db.execute(hierarchy_query, {"tag_id": tag.id})
                except Exception:
                    # Tag hierarchy table might not exist
                    pass
                
                # Then remove the tag itself
                logger.info(f"Removing tag '{tag_name}' (ID: {tag.id})...")
                db.execute(text("DELETE FROM tags WHERE id = :tag_id"), {"tag_id": tag.id})
                
                # Also remove from tag_normalizations if the table exists
                if tag_normalizations_exists:
                    try:
                        logger.info(f"Removing normalization entries for tag '{tag_name}'...")
                        # First try exact match
                        db.execute(
                            text("DELETE FROM tag_normalizations WHERE LOWER(normalized_name) = LOWER(:tag_name)"),
                            {"tag_name": tag_name}
                        )
                        # Also try with variations (case insensitive)
                        db.execute(
                            text("DELETE FROM tag_normalizations WHERE LOWER(original_name) = LOWER(:tag_name)"),
                            {"tag_name": tag_name}
                        )
                        logger.info(f"Successfully removed normalization entries for '{tag_name}'")
                    except Exception as e:
                        logger.error(f"Error removing normalization entries: {str(e)}")
                
                # Commit the changes
                db.commit()
                logger.info(f"Successfully removed tag '{tag_name}'")
            else:
                logger.info(f"Tag '{tag_name}' not found in database")
                
                # Even if tag not found, try to clean up tag_normalizations
                if tag_normalizations_exists:
                    try:
                        logger.info(f"Removing normalization entries for tag '{tag_name}'...")
                        db.execute(
                            text("DELETE FROM tag_normalizations WHERE LOWER(normalized_name) = LOWER(:tag_name) OR LOWER(original_name) = LOWER(:tag_name)"),
                            {"tag_name": tag_name}
                        )
                        db.commit()
                        logger.info(f"Successfully removed any normalization entries for '{tag_name}'")
                    except Exception as e:
                        logger.error(f"Error removing normalization entries: {str(e)}")
                        db.rollback()
                
        except Exception as e:
            logger.error(f"Error removing tag '{tag_name}': {str(e)}")
            db.rollback()
    
    logger.info("Finished removing problem tags")

if __name__ == "__main__":
    logger.info("Starting removal of problem tags")
    remove_problem_tags()
    logger.info("Script complete")
