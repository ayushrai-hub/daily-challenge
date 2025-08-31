#!/usr/bin/env python
"""
Script to identify and merge similar tags in the database.
This helps clean up tag inconsistencies by consolidating similar tags.

Usage:
    python merge_similar_tags.py --list  # List similar tags without merging
    python merge_similar_tags.py --merge  # Merge similar tags
    python merge_similar_tags.py --merge --tag-id <id> --target-id <id>  # Merge specific tags
"""

import sys
import os
import argparse
import logging
from typing import List, Dict, Tuple, Optional
from uuid import UUID
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import setup_logging, get_logger
from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.problem import Problem
from app.services.tag_normalizer import TagNormalizer
from app.repositories.tag import TagRepository

# Setup logging
setup_logging()
logger = get_logger()

def setup_arg_parser() -> argparse.ArgumentParser:
    """Set up and return the argument parser."""
    parser = argparse.ArgumentParser(description="Merge similar tags in the database")
    parser.add_argument("--list", action="store_true", help="List similar tags without merging")
    parser.add_argument("--merge", action="store_true", help="Merge similar tags")
    parser.add_argument("--tag-id", type=str, help="Source tag ID to merge from")
    parser.add_argument("--target-id", type=str, help="Target tag ID to merge into")
    parser.add_argument("--threshold", type=float, default=0.8, 
                       help="Similarity threshold (0.0-1.0) for automatic merging")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be merged without making changes")
    return parser

def find_similar_tags(db: Session, threshold: float = 0.8) -> List[Tuple[Tag, Tag, float]]:
    """
    Find pairs of tags that are similar based on name.
    
    Args:
        db: Database session
        threshold: Similarity threshold (0.0-1.0)
        
    Returns:
        List of tuples with (tag1, tag2, similarity_score)
    """
    # Get all tags
    tags = db.query(Tag).all()
    similar_pairs = []
    
    # Compare each tag with every other tag
    for i, tag1 in enumerate(tags):
        for tag2 in tags[i+1:]:
            # Skip comparison with itself
            if tag1.id == tag2.id:
                continue
                
            # Simple similarity calculation - can be enhanced
            name1 = tag1.name.lower()
            name2 = tag2.name.lower()
            
            # Check for exact case-insensitive match
            if name1 == name2:
                similar_pairs.append((tag1, tag2, 1.0))
                continue
                
            # Check for pluralization (simple s/es suffix)
            if name1.endswith('s') and name1[:-1] == name2:
                similar_pairs.append((tag1, tag2, 0.95))
                continue
                
            if name2.endswith('s') and name2[:-1] == name1:
                similar_pairs.append((tag1, tag2, 0.95))
                continue
                
            # Check for common prefix (at least 4 chars)
            min_prefix_len = 4
            prefix_len = min(len(name1), len(name2), min_prefix_len)
            if prefix_len >= min_prefix_len and name1[:prefix_len] == name2[:prefix_len]:
                # Calculate Levenshtein distance or use simpler similarity
                max_len = max(len(name1), len(name2))
                common_prefix_ratio = prefix_len / max_len
                
                # Char overlap similarity
                chars1 = set(name1)
                chars2 = set(name2)
                common_chars = len(chars1.intersection(chars2))
                all_chars = len(chars1.union(chars2))
                char_similarity = common_chars / all_chars if all_chars > 0 else 0
                
                # Combined similarity score
                similarity = (0.7 * char_similarity) + (0.3 * common_prefix_ratio)
                
                if similarity >= threshold:
                    similar_pairs.append((tag1, tag2, similarity))
    
    # Sort by similarity (highest first)
    similar_pairs.sort(key=lambda x: x[2], reverse=True)
    return similar_pairs

def merge_tags(db: Session, source_tag: Tag, target_tag: Tag, dry_run: bool = False) -> None:
    """
    Merge source tag into target tag.
    
    Args:
        db: Database session
        source_tag: Tag to merge from (will be deleted)
        target_tag: Tag to merge into (will be kept)
        dry_run: If True, show what would be done without making changes
    """
    logger.info(f"Merging tag '{source_tag.name}' (ID: {source_tag.id}) into '{target_tag.name}' (ID: {target_tag.id})")
    
    if dry_run:
        logger.info("[DRY RUN] No changes will be made")
    
    try:
        # 1. Update tag_normalizations referencing source_tag
        if not dry_run:
            tag_norm_count = db.execute(
                text("UPDATE tag_normalizations SET approved_tag_id = :target_id WHERE approved_tag_id = :source_id"),
                {"target_id": target_tag.id, "source_id": source_tag.id}
            ).rowcount
            logger.info(f"Updated {tag_norm_count} tag_normalizations references")
        else:
            logger.info(f"[DRY RUN] Would update tag_normalizations references")
        
        # 2. Update problem_tags junction table
        if not dry_run:
            # First check if there are any duplicate entries that need deletion
            duplicate_count = db.execute(text("""
                SELECT COUNT(*) FROM problem_tags 
                WHERE tag_id = :source_id AND problem_id IN (
                    SELECT problem_id FROM problem_tags WHERE tag_id = :target_id
                )
            """), {"source_id": source_tag.id, "target_id": target_tag.id}).scalar()
            
            if duplicate_count > 0:
                # Delete duplicates safely
                db.execute(text("""
                    DELETE FROM problem_tags 
                    WHERE tag_id = :source_id AND problem_id IN (
                        SELECT problem_id FROM problem_tags WHERE tag_id = :target_id
                    )
                """), {"source_id": source_tag.id, "target_id": target_tag.id})
                logger.info(f"Deleted {duplicate_count} duplicate problem_tags entries")
            
            # Update remaining problem_tags entries
            problem_tag_count = db.execute(
                text("UPDATE problem_tags SET tag_id = :target_id WHERE tag_id = :source_id"),
                {"target_id": target_tag.id, "source_id": source_tag.id}
            ).rowcount
            logger.info(f"Updated {problem_tag_count} problem_tags references")
        else:
            logger.info(f"[DRY RUN] Would update problem_tags references")
        
        # 3. Update user_tags junction table
        if not dry_run:
            # Check for duplicates first
            user_duplicate_count = db.execute(text("""
                SELECT COUNT(*) FROM user_tags 
                WHERE tag_id = :source_id AND user_id IN (
                    SELECT user_id FROM user_tags WHERE tag_id = :target_id
                )
            """), {"source_id": source_tag.id, "target_id": target_tag.id}).scalar()
            
            if user_duplicate_count > 0:
                # Delete duplicate user-tag connections
                db.execute(text("""
                    DELETE FROM user_tags 
                    WHERE tag_id = :source_id AND user_id IN (
                        SELECT user_id FROM user_tags WHERE tag_id = :target_id
                    )
                """), {"source_id": source_tag.id, "target_id": target_tag.id})
                logger.info(f"Deleted {user_duplicate_count} duplicate user_tags entries")
            
            # Update remaining user_tags entries
            user_tag_count = db.execute(
                text("UPDATE user_tags SET tag_id = :target_id WHERE tag_id = :source_id"),
                {"target_id": target_tag.id, "source_id": source_tag.id}
            ).rowcount
            logger.info(f"Updated {user_tag_count} user_tags references")
        else:
            logger.info(f"[DRY RUN] Would update user_tags references")
        
        # 4. Update tag hierarchy - parent relationships
        if not dry_run:
            # Check for duplicate hierarchy entries
            hier_parent_duplicate_count = db.execute(text("""
                SELECT COUNT(*) FROM tag_hierarchy 
                WHERE child_tag_id = :child_id AND parent_tag_id = :source_id AND 
                      EXISTS (SELECT 1 FROM tag_hierarchy WHERE child_tag_id = :child_id AND parent_tag_id = :target_id)
            """), {"child_id": source_tag.id, "source_id": source_tag.id, "target_id": target_tag.id}).scalar()
            
            if hier_parent_duplicate_count > 0:
                # Delete duplicates
                db.execute(text("""
                    DELETE FROM tag_hierarchy 
                    WHERE child_tag_id = :child_id AND parent_tag_id = :source_id AND 
                          EXISTS (SELECT 1 FROM tag_hierarchy WHERE child_tag_id = :child_id AND parent_tag_id = :target_id)
                """), {"child_id": source_tag.id, "source_id": source_tag.id, "target_id": target_tag.id})
                logger.info(f"Deleted {hier_parent_duplicate_count} duplicate tag_hierarchy parent entries")
            
            # Update remaining parent entries
            hier_parent_count = db.execute(
                text("UPDATE tag_hierarchy SET parent_tag_id = :target_id WHERE parent_tag_id = :source_id"),
                {"target_id": target_tag.id, "source_id": source_tag.id}
            ).rowcount
            logger.info(f"Updated {hier_parent_count} tag_hierarchy parent references")
        else:
            logger.info(f"[DRY RUN] Would update tag_hierarchy parent references")
        
        # 5. Update tag hierarchy - child relationships
        if not dry_run:
            # Check for duplicate hierarchy entries
            hier_child_duplicate_count = db.execute(text("""
                SELECT COUNT(*) FROM tag_hierarchy 
                WHERE parent_tag_id = :parent_id AND child_tag_id = :source_id AND 
                      EXISTS (SELECT 1 FROM tag_hierarchy WHERE parent_tag_id = :parent_id AND child_tag_id = :target_id)
            """), {"parent_id": source_tag.id, "source_id": source_tag.id, "target_id": target_tag.id}).scalar()
            
            if hier_child_duplicate_count > 0:
                # Delete duplicates
                db.execute(text("""
                    DELETE FROM tag_hierarchy 
                    WHERE parent_tag_id = :parent_id AND child_tag_id = :source_id AND 
                          EXISTS (SELECT 1 FROM tag_hierarchy WHERE parent_tag_id = :parent_id AND child_tag_id = :target_id)
                """), {"parent_id": source_tag.id, "source_id": source_tag.id, "target_id": target_tag.id})
                logger.info(f"Deleted {hier_child_duplicate_count} duplicate tag_hierarchy child entries")
            
            # Update remaining child entries
            hier_child_count = db.execute(
                text("UPDATE tag_hierarchy SET child_tag_id = :target_id WHERE child_tag_id = :source_id"),
                {"target_id": target_tag.id, "source_id": source_tag.id}
            ).rowcount
            logger.info(f"Updated {hier_child_count} tag_hierarchy child references")
        else:
            logger.info(f"[DRY RUN] Would update tag_hierarchy child references")
        
        # Commit the reference updates first to avoid foreign key issues
        if not dry_run:
            db.commit()
            logger.info(f"Successfully updated all references to the tag")
        
        # 6. Delete the source tag in a separate transaction
        if not dry_run:
            # Refresh the source tag to ensure we have the latest state
            db.refresh(source_tag)
            db.delete(source_tag)
            db.commit()
            logger.info(f"Deleted source tag '{source_tag.name}'")
        else:
            logger.info(f"[DRY RUN] Would delete source tag '{source_tag.name}'")
            logger.info(f"[DRY RUN] No changes were made")
            
    except Exception as e:
        if not dry_run:
            db.rollback()
            logger.error(f"Error merging tags: {str(e)}")
            logger.exception("Detailed error information:")
        raise

def main():
    """Main function to run the script."""
    parser = setup_arg_parser()
    args = parser.parse_args()
    
    # Get database session
    db = next(get_db())
    
    if args.list:
        # List similar tags
        similar_tags = find_similar_tags(db, args.threshold)
        
        if not similar_tags:
            logger.info("No similar tags found.")
            return
            
        logger.info(f"Found {len(similar_tags)} pairs of similar tags:")
        for tag1, tag2, similarity in similar_tags:
            logger.info(f"Similarity {similarity:.2f}: '{tag1.name}' (ID: {tag1.id}) - '{tag2.name}' (ID: {tag2.id})")
    
    elif args.merge:
        if args.tag_id and args.target_id:
            # Merge specific tags
            try:
                source_id = UUID(args.tag_id)
                target_id = UUID(args.target_id)
            except ValueError:
                logger.error("Invalid tag ID format. Must be valid UUID.")
                return
                
            source_tag = db.query(Tag).filter(Tag.id == source_id).first()
            target_tag = db.query(Tag).filter(Tag.id == target_id).first()
            
            if not source_tag:
                logger.error(f"Source tag with ID {source_id} not found.")
                return
                
            if not target_tag:
                logger.error(f"Target tag with ID {target_id} not found.")
                return
                
            merge_tags(db, source_tag, target_tag, args.dry_run)
        
        else:
            # Auto-merge similar tags
            similar_tags = find_similar_tags(db, args.threshold)
            
            if not similar_tags:
                logger.info("No similar tags found for merging.")
                return
                
            # Process each pair
            for tag1, tag2, similarity in similar_tags:
                logger.info(f"Considering tags for merge: '{tag1.name}' and '{tag2.name}' (similarity: {similarity:.2f})")
                
                # Decide which tag to keep (prefer the one with more problems)
                problems_count1 = db.query(func.count()).select_from(Problem).join(Problem.tags).filter(Tag.id == tag1.id).scalar() or 0
                problems_count2 = db.query(func.count()).select_from(Problem).join(Problem.tags).filter(Tag.id == tag2.id).scalar() or 0
                
                # Prefer to keep the tag with more relationships
                if problems_count1 >= problems_count2:
                    target_tag, source_tag = tag1, tag2
                else:
                    target_tag, source_tag = tag2, tag1
                    
                merge_tags(db, source_tag, target_tag, args.dry_run)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
