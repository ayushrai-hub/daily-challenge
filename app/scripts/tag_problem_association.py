#!/usr/bin/env python3
"""
Script to associate tags with relevant problems.
This script can be used to:
1. Associate a single tag with all relevant problems
2. Run associations for all approved tags

Usage:
  python -m app.scripts.tag_problem_association --tag-id=<tag_id>
  python -m app.scripts.tag_problem_association --tag-name=<tag_name>
  python -m app.scripts.tag_problem_association --all-tags
"""

import os
import sys
import argparse
from uuid import UUID
from typing import List, Optional, Set

# Set up path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import get_db
from app.db.models.tag import Tag
from app.db.models.problem import Problem
from app.repositories.tag import TagRepository
from app.core.logging import get_logger
from sqlalchemy import or_, cast, String

logger = get_logger()

def associate_tag_with_problems(tag_id: UUID, db_session=None) -> int:
    """
    Associate a tag with all relevant problems based on tag name.
    
    Args:
        tag_id: UUID of the tag to associate
        db_session: Optional database session
        
    Returns:
        Number of problems that were associated with the tag
    """
    close_db = False
    if not db_session:
        db_session = next(get_db())
        close_db = True
    
    try:
        # Get the tag
        tag = db_session.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            logger.error(f"Tag with ID {tag_id} not found")
            return 0
            
        tag_name = tag.name
        logger.info(f"Associating tag '{tag_name}' (ID: {tag_id}) with relevant problems")
        
        # Search for problems containing the tag name in title
        problems_with_tag_in_title = db_session.query(Problem).filter(
            Problem.title.ilike(f"%{tag_name}%")
        ).all()
        
        # Also search in description and problem_metadata
        problems_with_tag_in_content = db_session.query(Problem).filter(
            or_(
                Problem.description.ilike(f"%{tag_name}%"),
                cast(Problem.problem_metadata, String).ilike(f"%{tag_name}%")
            )
        ).all()
        
        # Combine and deduplicate results
        all_problems = set(problems_with_tag_in_title + problems_with_tag_in_content)
        
        # Associate tag with each relevant problem
        association_count = 0
        for problem in all_problems:
            # Check if tag is already associated with the problem
            if tag not in problem.tags:
                problem.tags.append(tag)
                association_count += 1
                logger.info(f"Associated tag '{tag_name}' with problem: {problem.title} (ID: {problem.id})")
        
        # Commit changes
        db_session.commit()
        
        logger.info(f"Associated tag '{tag_name}' with {association_count} problems")
        return association_count
        
    except Exception as e:
        logger.error(f"Error associating tag with problems: {str(e)}")
        db_session.rollback()
        return 0
    finally:
        if close_db:
            db_session.close()

def associate_tag_by_name(tag_name: str) -> int:
    """
    Find a tag by name and associate it with relevant problems.
    
    Args:
        tag_name: Name of the tag to associate
        
    Returns:
        Number of problems that were associated with the tag
    """
    db_session = next(get_db())
    try:
        # Find the tag by name (case insensitive)
        tag = db_session.query(Tag).filter(Tag.name.ilike(tag_name)).first()
        if not tag:
            logger.error(f"Tag with name '{tag_name}' not found")
            return 0
            
        return associate_tag_with_problems(tag.id, db_session)
    finally:
        db_session.close()

def associate_all_tags() -> int:
    """
    Associate all approved tags with relevant problems.
    
    Returns:
        Total number of tag-problem associations created
    """
    db_session = next(get_db())
    try:
        # Get all tags
        tags = db_session.query(Tag).all()
        logger.info(f"Found {len(tags)} tags to process")
        
        total_associations = 0
        for tag in tags:
            associations = associate_tag_with_problems(tag.id, db_session)
            total_associations += associations
            
        return total_associations
    finally:
        db_session.close()

def main():
    parser = argparse.ArgumentParser(description='Associate tags with relevant problems')
    tag_group = parser.add_mutually_exclusive_group(required=True)
    tag_group.add_argument('--tag-id', type=str, help='UUID of the tag to associate')
    tag_group.add_argument('--tag-name', type=str, help='Name of the tag to associate')
    tag_group.add_argument('--all-tags', action='store_true', help='Process all tags')
    
    args = parser.parse_args()
    
    if args.tag_id:
        try:
            tag_id = UUID(args.tag_id)
            count = associate_tag_with_problems(tag_id)
        except ValueError:
            logger.error(f"Invalid UUID format: {args.tag_id}")
            return 1
    elif args.tag_name:
        count = associate_tag_by_name(args.tag_name)
    elif args.all_tags:
        count = associate_all_tags()
        
    logger.info(f"Created a total of {count} tag-problem associations")
    return 0

if __name__ == "__main__":
    sys.exit(main())
