#!/usr/bin/env python3
"""
Tag Analysis and Repair Script

Analyzes the current state of tags in the database and fixes mapping issues:
1. Identifies duplicate tags (case-insensitive)
2. Analyzes the tag hierarchy and parent-child relationships
3. Identifies orphan tags missing parent categories
4. Outputs statistics and repair suggestions
5. Performs cleaning and mapping operations

This helps ensure problems are properly linked to tags with the correct hierarchy.
"""

import sys
import os
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_
import logging
from typing import Dict, List, Set, Tuple
import uuid
import json
from collections import defaultdict
from pprint import pprint

# Add project root to path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.session import get_db
from app.db.models.tag import Tag, TagType
from app.db.models.problem import Problem
from app.db.models.association_tables import problem_tags
from app.services.tag_mapper import get_tag_mapper, TagMapper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_tags(db: Session) -> Dict:
    """
    Analyze all tags in the database and generate statistics.
    """
    logger.info("Analyzing tags in database...")
    
    # Get all tags
    tags = db.query(Tag).options(joinedload(Tag.problems)).all()
    
    # Get tag mapper service
    tag_mapper = get_tag_mapper(db)
    
    # Count tags by type
    tag_types = {}
    for tag_type in TagType:
        tag_types[tag_type.name] = len([t for t in tags if t.tag_type == tag_type])
    
    # Count tags by parent
    parent_counts = defaultdict(int)
    for tag in tags:
        if tag.parent_tag_id:
            parent_tag = next((t for t in tags if t.id == tag.parent_tag_id), None)
            if parent_tag:
                parent_counts[parent_tag.name] += 1
    
    # Find duplicate tags (case-insensitive)
    tags_by_lowercase = defaultdict(list)
    for tag in tags:
        tags_by_lowercase[tag.name.lower()].append(tag)
    
    duplicates = {name: tags for name, tags in tags_by_lowercase.items() if len(tags) > 1}
    
    # Find orphaned tags (no parent)
    orphaned_tags = [tag for tag in tags if not tag.parent_tag_id and tag.tag_type != TagType.category]
    
    # Find inconsistent casing
    inconsistent_casing = []
    for tag in tags:
        normalized = tag_mapper.normalize_tag_name(tag.name)
        if normalized != tag.name:
            inconsistent_casing.append((tag.name, normalized))
    
    # Find unused tags (not associated with any problems)
    unused_tags = [tag for tag in tags if not tag.problems or len(tag.problems) == 0]
    
    # Find problems with duplicate tag associations (different cases)
    problems = db.query(Problem).options(joinedload(Problem.tags)).all()
    problems_with_duplicate_tags = []
    
    for problem in problems:
        tag_names_lower = {}
        for tag in problem.tags:
            tag_lower = tag.name.lower()
            if tag_lower in tag_names_lower:
                problems_with_duplicate_tags.append({
                    "problem_id": str(problem.id),
                    "problem_title": problem.title,
                    "duplicate_tags": [tag_names_lower[tag_lower].name, tag.name]
                })
                break
            tag_names_lower[tag_lower] = tag
    
    # Generate statistics
    stats = {
        "total_tags": len(tags),
        "tag_types": tag_types,
        "parent_counts": dict(parent_counts),
        "duplicate_tags": {name: [t.name for t in tags] for name, tags in duplicates.items()},
        "orphaned_tags": [t.name for t in orphaned_tags],
        "inconsistent_casing": dict(inconsistent_casing),
        "unused_tags": [t.name for t in unused_tags],
        "problems_with_duplicate_tags": problems_with_duplicate_tags,
    }
    
    return stats

def fix_tag_hierarchy(db: Session) -> Dict:
    """
    Fix tag hierarchy issues:
    1. Normalize tag names
    2. Merge duplicate tags
    3. Assign parent categories to orphaned tags
    4. Update problem tag associations
    """
    logger.info("Fixing tag hierarchy...")
    
    # Get tag mapper service
    tag_mapper = get_tag_mapper(db)
    
    # Step 1: Normalize tag names
    tags = db.query(Tag).all()
    normalization_count = 0
    
    for tag in tags:
        normalized_name = tag_mapper.normalize_tag_name(tag.name)
        if normalized_name != tag.name:
            logger.info(f"Normalizing tag: '{tag.name}' -> '{normalized_name}'")
            tag.name = normalized_name
            normalization_count += 1
    
    db.commit()
    
    # Step 2: Merge duplicate tags
    merge_stats = tag_mapper.merge_duplicate_tags()
    
    # Step 3: Assign parent categories to orphaned tags
    parent_categories = tag_mapper.get_or_create_parent_categories()
    
    orphaned_tags = db.query(Tag).filter(Tag.parent_tag_id == None, Tag.tag_type != TagType.category).all()
    orphan_assignment_count = 0
    
    for tag in orphaned_tags:
        suitable_categories = tag_mapper.find_suitable_parent_categories(tag.name)
        if suitable_categories:
            primary_category = suitable_categories[0]
            parent_tag = parent_categories.get(primary_category)
            if parent_tag:
                logger.info(f"Assigning orphaned tag '{tag.name}' to parent category '{primary_category}'")
                tag.parent_tag_id = parent_tag.id
                orphan_assignment_count += 1
    
    db.commit()
    
    # Step 4: Check problem tag associations
    problems = db.query(Problem).options(joinedload(Problem.tags)).all()
    problem_tag_fix_count = 0
    
    for problem in problems:
        # Group problem tags by lowercase name
        tag_map = defaultdict(list)
        for tag in problem.tags:
            tag_map[tag.name.lower()].append(tag)
        
        # Fix any duplicate tags (keep only one per lowercase name)
        for lowercase_name, tags in tag_map.items():
            if len(tags) > 1:
                # Keep the normalized tag, remove others
                best_tag = None
                for tag in tags:
                    if tag.name == tag_mapper.normalize_tag_name(tag.name):
                        best_tag = tag
                        break
                
                if not best_tag:
                    # If no normalized tag found, keep the first one
                    best_tag = tags[0]
                
                # Remove all other tags
                for tag in tags:
                    if tag != best_tag and tag in problem.tags:
                        problem.tags.remove(tag)
                        problem_tag_fix_count += 1
    
    db.commit()
    
    # Step 5: Check if any problems are missing key tags based on description
    # This would be too complex for this script, but we could log a reminder
    
    fix_stats = {
        "normalized_tags": normalization_count,
        "merged_tags": merge_stats,
        "orphan_assignments": orphan_assignment_count,
        "problem_tag_fixes": problem_tag_fix_count
    }
    
    return fix_stats

def print_tag_hierarchy(db: Session):
    """
    Print the current tag hierarchy in a tree-like format for visualization.
    """
    # Get all tags
    tags = db.query(Tag).all()
    
    # Create a map of parent_id -> list of child tags
    children_map = defaultdict(list)
    for tag in tags:
        parent_id = tag.parent_tag_id if tag.parent_tag_id else None
        children_map[parent_id].append(tag)
    
    # Print root categories first (tags with parent_id = None)
    logger.info("\n--- TAG HIERARCHY ---")
    
    def print_tag_tree(parent_id, indent=0):
        for tag in sorted(children_map.get(parent_id, []), key=lambda t: t.name):
            problem_count = len(getattr(tag, 'problems', []))
            logger.info(f"{' ' * indent}|- {tag.name} [{tag.tag_type.name}] ({problem_count} problems)")
            print_tag_tree(tag.id, indent + 4)
    
    print_tag_tree(None)

def main():
    """Main entry point for the script"""
    logger.info("Starting tag analysis")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Analyze tags
        stats = analyze_tags(db)
        logger.info("Tag Analysis Results:")
        pretty_stats = json.dumps(stats, indent=2)
        logger.info(pretty_stats)
        
        # Only fix issues if requested
        if len(sys.argv) > 1 and sys.argv[1] == '--fix':
            # Fix tag issues
            fix_stats = fix_tag_hierarchy(db)
            logger.info(f"Tag fixes applied: {fix_stats}")
            
            # Print updated hierarchy
            print_tag_hierarchy(db)
        else:
            logger.info("Run with --fix to apply fixes to the tag hierarchy")
        
    except Exception as e:
        logger.error(f"Error in tag analysis/fixing: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
