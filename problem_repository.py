"""
Repository functions for creating problems with tags.
Extends the functionality of the core problem repository.
"""
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session  # Add synchronous Session for sync operations
from sqlalchemy.future import select
from uuid import UUID

from app.db.models.problem import Problem, DifficultyLevel, VettingTier, ProblemStatus
from app.db.models.tag import Tag
from app.core.logging import get_logger
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.services.tag_mapper import get_tag_mapper

logger = get_logger()


async def create_problem_with_tags(
    session: AsyncSession,
    problem_data: Dict[str, Any]
) -> UUID:
    """
    Create a new problem with associated tags.
    
    Args:
        session: Async database session
        problem_data: Dictionary containing problem fields and tags
            Required fields:
            - title: Problem title
            - description: Problem description
            - difficulty_level: Problem difficulty (DifficultyLevel enum)
            Optional fields:
            - solution: Problem solution
            - status: Problem status (ProblemStatus enum)
            - vetting_tier: Vetting tier (VettingTier enum)
            - content_source_id: Associated content source ID
            - approved_at: DateTime when problem was approved
            - tags: List of tag names to associate with the problem
    
    Returns:
        UUID of the created problem
        
    Raises:
        ValueError: If required fields are missing
    """
    # Extract tags before creating problem
    tag_names = problem_data.pop("tags", [])
    
    # Validate required fields
    if not problem_data.get("title"):
        raise ValueError("Problem title is required")
    if not problem_data.get("description"):
        raise ValueError("Problem description is required")
    if not problem_data.get("difficulty_level"):
        raise ValueError("Problem difficulty level is required")
    
    # Create the problem
    problem = Problem(
        title=problem_data["title"],
        description=problem_data["description"],
        solution=problem_data.get("solution"),
        difficulty_level=problem_data["difficulty_level"],
        status=problem_data.get("status", ProblemStatus.draft),
        vetting_tier=problem_data.get("vetting_tier", VettingTier.tier3_needs_review),
        content_source_id=problem_data.get("content_source_id"),
        approved_at=problem_data.get("approved_at")
    )
    
    session.add(problem)
    await session.flush()  # Flush to get the problem ID
    
    # Process tags: first try to find existing tags by name, create new ones if needed
    if tag_names:
        # Convert tag names to lowercase for consistency
        tag_names = [name.lower() for name in tag_names]
        
        # Find existing tags with these names
        existing_tags_query = await session.execute(
            select(Tag).where(Tag.name.in_(tag_names))
        )
        existing_tags = existing_tags_query.scalars().all()
        existing_tag_names = {tag.name for tag in existing_tags}
        
        # Create any new tags that don't exist
        for tag_name in tag_names:
            if tag_name not in existing_tag_names:
                new_tag = Tag(name=tag_name)
                session.add(new_tag)
                existing_tags.append(new_tag)
        
        await session.flush()  # Flush to ensure tags have IDs
        
        # Associate tags with the problem
        problem.tags = existing_tags
    
    # Commit the transaction
    await session.commit()
    await session.refresh(problem)
    
    logger.info(f"Created problem '{problem.title}' with ID {problem.id}")
    
    return problem.id


def create_problem_with_tags_sync(
    db: Session,
    problem_data: Dict[str, Any]
) -> UUID:
    """
    Synchronous version of create_problem_with_tags with tag standardization and
    automatic parent-child tag relationship creation.
    
    Args:
        db: Synchronous database session
        problem_data: Dictionary containing problem fields and tags
            Required fields:
            - title: Problem title
            - description: Problem description
            - difficulty_level: Problem difficulty (DifficultyLevel enum)
            Optional fields:
            - solution: Problem solution
            - status: Problem status (ProblemStatus enum)
            - vetting_tier: Vetting tier (VettingTier enum)
            - content_source_id: Associated content source ID
            - approved_at: DateTime when problem was approved
            - tags: List of tag names to associate with the problem
    
    Returns:
        UUID of the created problem
        
    Raises:
        ValueError: If required fields are missing
    """
    # Extract tags before creating problem
    tag_names = problem_data.pop("tags", [])
    
    # Validate required fields
    if not problem_data.get("title"):
        raise ValueError("Problem title is required")
    if not problem_data.get("description"):
        raise ValueError("Problem description is required")
    if not problem_data.get("difficulty_level"):
        raise ValueError("Problem difficulty level is required")
    
    # Create the problem
    problem = Problem(
        title=problem_data["title"],
        description=problem_data["description"],
        solution=problem_data.get("solution"),
        difficulty_level=problem_data["difficulty_level"],
        status=problem_data.get("status", ProblemStatus.draft),
        vetting_tier=problem_data.get("vetting_tier", VettingTier.tier3_needs_review),
        content_source_id=problem_data.get("content_source_id"),
        approved_at=problem_data.get("approved_at")
    )
    
    db.add(problem)
    db.flush()  # Flush to get the problem ID
    
    # Process tags: first try to find existing tags by name, create new ones if needed
    if tag_names:
        # Initialize tag repository and normalizer
        tag_repo = TagRepository(db)
        tag_normalizer = TagNormalizer(tag_repo)
        
        # Normalize tag names for proper capitalization and mapping to existing tags
        normalized_tags = tag_normalizer.normalize_tag_names(tag_names)
        
        print(f"Processing tags for problem '{problem.title}': {tag_names}")
        logger.info(f"Processing tags for problem '{problem.title}': {tag_names}")
        print(f"Normalized tags: {normalized_tags}")
        logger.info(f"Normalized tags: {normalized_tags}")
        
        # Apply tag standardization and hierarchy creation
        standardized_tags = standardize_and_organize_tags(db, normalized_tags)
        print(f"Standardized tags: {standardized_tags}")
        logger.info(f"Standardized tags: {standardized_tags}")
        
        # First build a complete hierarchy of parent categories that might be needed
        pending_parents = set()
        parent_hierarchy = {}
        
        # Identify all needed parent categories
        for tag_info in standardized_tags.values():
            parent = tag_info['parent_category']
            if parent:
                pending_parents.add(parent)
                current = parent
                while current:
                    # Check if this parent has its own parent
                    for tag_name, info in tag_mapping.items():
                        if info['std_name'] == current and info['parent']:
                            parent_of_parent = info['parent']
                            parent_hierarchy[current] = parent_of_parent
                            pending_parents.add(parent_of_parent)
                            current = parent_of_parent
                            break
                    else:
                        current = None
                            
        print(f"Needed parent categories: {pending_parents}")
        logger.info(f"Needed parent categories: {pending_parents}")
        print(f"Parent hierarchy: {parent_hierarchy}")
        logger.info(f"Parent hierarchy: {parent_hierarchy}")
        
        # Create all parent tags first (from top of hierarchy down)
        created_parent_tags = {}
        
        # First find all existing parent tags
        if pending_parents:
            parent_query = db.execute(
                select(Tag).where(Tag.name.in_(pending_parents))
            )
            existing_parents = parent_query.scalars().all()
            
            for parent in existing_parents:
                created_parent_tags[parent.name] = parent
                print(f"Found existing parent tag: {parent.name} (ID: {parent.id})")
                logger.info(f"Found existing parent tag: {parent.name} (ID: {parent.id})")
        
        # Create any missing parent tags (from top of hierarchy down)
        # Start with root parents (those with no parents themselves)
        root_parents = [p for p in pending_parents if p not in parent_hierarchy]
        for parent_name in root_parents:
            if parent_name not in created_parent_tags:
                parent_tag = Tag(name=parent_name)
                db.add(parent_tag)
                db.flush()  # Get ID right away
                created_parent_tags[parent_name] = parent_tag
                print(f"Created root parent tag: {parent_name} (ID: {parent_tag.id})")
                logger.info(f"Created root parent tag: {parent_name} (ID: {parent_tag.id})")
        
        # Now create the rest of the parent tags in order of their hierarchy
        remaining_parents = pending_parents - set(created_parent_tags.keys())
        while remaining_parents:
            for parent_name in list(remaining_parents):  # Use list() to avoid modifying during iteration
                if parent_name in parent_hierarchy and parent_hierarchy[parent_name] in created_parent_tags:
                    # The parent of this tag exists, so we can create it now
                    parent_of_parent = created_parent_tags[parent_hierarchy[parent_name]]
                    parent_tag = Tag(
                        name=parent_name, 
                        parent_tag_id=parent_of_parent.id
                    )
                    db.add(parent_tag)
                    db.flush()  # Get ID right away
                    created_parent_tags[parent_name] = parent_tag
                    remaining_parents.remove(parent_name)
                    print(f"Created child parent tag: {parent_name} (ID: {parent_tag.id}) with parent: {parent_of_parent.name}")
                    logger.info(f"Created child parent tag: {parent_name} (ID: {parent_tag.id}) with parent: {parent_of_parent.name}")
            
            # If we didn't make progress in this iteration, break to avoid infinite loop
            if not any(parent_name in parent_hierarchy and parent_hierarchy[parent_name] in created_parent_tags 
                      for parent_name in remaining_parents):
                # Create any remaining parents without their proper hierarchy
                for parent_name in remaining_parents:
                    parent_tag = Tag(name=parent_name)
                    db.add(parent_tag)
                    db.flush()
                    created_parent_tags[parent_name] = parent_tag
                    print(f"Created orphaned parent tag: {parent_name} (ID: {parent_tag.id})")
                    logger.info(f"Created orphaned parent tag: {parent_name} (ID: {parent_tag.id})")
                break
        
        # Now create or update all the actual tags
        all_tags = []
        
        for tag_name, tag_info in standardized_tags.items():
            # Try to find existing tag using case-insensitive matching
            tag_repo = TagRepository(db)
            tag = tag_repo.get_by_name_case_insensitive(tag_name)
            
            # Get parent if applicable
            parent_tag_id = None
            parent_name = tag_info['parent_category']
            if parent_name and parent_name in created_parent_tags:
                parent_tag_id = created_parent_tags[parent_name].id
                
            if not tag:
                # Create new tag with parent relationship
                tag = Tag(
                    name=tag_name,
                    parent_tag_id=parent_tag_id
                )
                db.add(tag)
                print(f"Created new tag: {tag_name} with parent ID: {parent_tag_id}")
                logger.info(f"Created new tag: {tag_name} with parent ID: {parent_tag_id}")
            else:
                # Update existing tag's parent if needed
                if tag.parent_tag_id != parent_tag_id:
                    tag.parent_tag_id = parent_tag_id
                    print(f"Updated existing tag: {tag_name} with parent ID: {parent_tag_id}")
                    logger.info(f"Updated existing tag: {tag_name} with parent ID: {parent_tag_id}")
                else:
                    print(f"Using existing tag: {tag_name} (ID: {tag.id}) without changes")
                    logger.info(f"Using existing tag: {tag_name} (ID: {tag.id}) without changes")
            
            all_tags.append(tag)
        
        # Flush to ensure all tags have IDs
        db.flush()
        
        # Associate tags with the problem
        problem.tags = all_tags
        print(f"Associated problem '{problem.title}' with {len(all_tags)} tags")
        logger.info(f"Associated problem '{problem.title}' with {len(all_tags)} tags")
    
    # Commit the transaction
    db.commit()
    db.refresh(problem)
    
    print(f"Created problem '{problem.title}' with ID {problem.id} (sync)")
    logger.info(f"Created problem '{problem.title}' with ID {problem.id} (sync)")
    
    return problem.id


def standardize_and_organize_tags(db: Session, tag_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Standardize tags and organize them into hierarchical categories.
    
    Args:
        db: Database session
        tag_names: List of tag names to standardize and organize
        
    Returns:
        Dictionary mapping standardized tag names to their parent categories and metadata
    """
    # Define tag mappings and categories
    tag_mapping = {
        # Programming Languages
        'python': {'std_name': 'python', 'parent': 'languages'},
        'java': {'std_name': 'java', 'parent': 'languages'},
        'javascript': {'std_name': 'javascript', 'parent': 'languages'},
        'typescript': {'std_name': 'typescript', 'parent': 'languages'},
        'js': {'std_name': 'javascript', 'parent': 'languages'},
        'ts': {'std_name': 'typescript', 'parent': 'languages'},
        'go': {'std_name': 'go', 'parent': 'languages'},
        'c++': {'std_name': 'c++', 'parent': 'languages'},
        'c#': {'std_name': 'c#', 'parent': 'languages'},
        'php': {'std_name': 'php', 'parent': 'languages'},
        'ruby': {'std_name': 'ruby', 'parent': 'languages'},
        'rust': {'std_name': 'rust', 'parent': 'languages'},
        'kotlin': {'std_name': 'kotlin', 'parent': 'languages'},
        'scala': {'std_name': 'scala', 'parent': 'languages'},
        'swift': {'std_name': 'swift', 'parent': 'languages'},
        
        # Web Technologies
        'react': {'std_name': 'react', 'parent': 'javascript'},
        'angular': {'std_name': 'angular', 'parent': 'javascript'},
        'vue': {'std_name': 'vue', 'parent': 'javascript'},
        'node': {'std_name': 'node.js', 'parent': 'javascript'},
        'nodejs': {'std_name': 'node.js', 'parent': 'javascript'},
        'express': {'std_name': 'express', 'parent': 'javascript'},
        'django': {'std_name': 'django', 'parent': 'python'},
        'flask': {'std_name': 'flask', 'parent': 'python'},
        'fastapi': {'std_name': 'fastapi', 'parent': 'python'},
        
        # Data Structures
        'arrays': {'std_name': 'arrays', 'parent': 'data structures'},
        'array': {'std_name': 'arrays', 'parent': 'data structures'},
        'linked lists': {'std_name': 'linked lists', 'parent': 'data structures'},
        'linked list': {'std_name': 'linked lists', 'parent': 'data structures'},
        'stacks': {'std_name': 'stacks', 'parent': 'data structures'},
        'stack': {'std_name': 'stacks', 'parent': 'data structures'},
        'queues': {'std_name': 'queues', 'parent': 'data structures'},
        'queue': {'std_name': 'queues', 'parent': 'data structures'},
        'trees': {'std_name': 'trees', 'parent': 'data structures'},
        'tree': {'std_name': 'trees', 'parent': 'data structures'},
        'graphs': {'std_name': 'graphs', 'parent': 'data structures'},
        'graph': {'std_name': 'graphs', 'parent': 'data structures'},
        'hash table': {'std_name': 'hash tables', 'parent': 'data structures'},
        'hash tables': {'std_name': 'hash tables', 'parent': 'data structures'},
        'hashmap': {'std_name': 'hash tables', 'parent': 'data structures'},
        'heap': {'std_name': 'heaps', 'parent': 'data structures'},
        'heaps': {'std_name': 'heaps', 'parent': 'data structures'},
        
        # Algorithms
        'recursion': {'std_name': 'recursion', 'parent': 'algorithms'},
        'dynamic programming': {'std_name': 'dynamic programming', 'parent': 'algorithms'},
        'dp': {'std_name': 'dynamic programming', 'parent': 'algorithms'},
        'greedy': {'std_name': 'greedy', 'parent': 'algorithms'},
        'greedy algorithm': {'std_name': 'greedy', 'parent': 'algorithms'},
        'sorting': {'std_name': 'sorting', 'parent': 'algorithms'},
        'searching': {'std_name': 'searching', 'parent': 'algorithms'},
        'binary search': {'std_name': 'binary search', 'parent': 'algorithms'},
        'dfs': {'std_name': 'depth-first search', 'parent': 'algorithms'},
        'bfs': {'std_name': 'breadth-first search', 'parent': 'algorithms'},
        'depth-first search': {'std_name': 'depth-first search', 'parent': 'algorithms'},
        'breadth-first search': {'std_name': 'breadth-first search', 'parent': 'algorithms'},
        
        # Linting and Static Analysis
        'eslint': {'std_name': 'eslint', 'parent': 'linting'},
        'static analysis': {'std_name': 'static analysis', 'parent': 'code quality'},
        'static-analysis': {'std_name': 'static analysis', 'parent': 'code quality'},
        'linting': {'std_name': 'linting', 'parent': 'code quality'},
        'lint': {'std_name': 'linting', 'parent': 'code quality'},
        'code style': {'std_name': 'code style', 'parent': 'code quality'},
        'code quality': {'std_name': 'code quality', 'parent': None},
        'import restrictions': {'std_name': 'import restrictions', 'parent': 'code organization'},
        'import-restrictions': {'std_name': 'import restrictions', 'parent': 'code organization'},
        'import': {'std_name': 'imports', 'parent': 'code organization'},
        'imports': {'std_name': 'imports', 'parent': 'code organization'},
        'import-statements': {'std_name': 'imports', 'parent': 'code organization'},
        'code organization': {'std_name': 'code organization', 'parent': 'code quality'},
        'code-organization': {'std_name': 'code organization', 'parent': 'code quality'},
        'code layers': {'std_name': 'code layers', 'parent': 'code organization'},
        'code-layers': {'std_name': 'code layers', 'parent': 'code organization'},
        'code-architecture': {'std_name': 'architecture', 'parent': 'code quality'},
        'architectural-patterns': {'std_name': 'architecture', 'parent': 'code quality'},
        'architecture': {'std_name': 'architecture', 'parent': 'code quality'},
        'validation': {'std_name': 'validation', 'parent': 'code quality'},
        'coding-conventions': {'std_name': 'coding conventions', 'parent': 'code quality'},
        'coding-standards': {'std_name': 'coding conventions', 'parent': 'code quality'},
        
        # Difficulty levels mapped to the standard levels
        'easy': {'std_name': 'easy', 'parent': 'difficulty'},
        'medium': {'std_name': 'medium', 'parent': 'difficulty'},
        'hard': {'std_name': 'hard', 'parent': 'difficulty'},
    }
    
    standardized_tags = {}
    
    # Process each tag
    for tag in tag_names:
        # Skip empty tags
        if not tag:
            continue
            
        # Check if tag exists in our mapping
        if tag in tag_mapping:
            std_name = tag_mapping[tag]['std_name']
            parent = tag_mapping[tag]['parent']
        else:
            # For unknown tags, keep the original name and no parent
            std_name = tag
            parent = None
        
        # Add standardized tag to result
        standardized_tags[std_name] = {
            'parent_category': parent,
            'original_tag': tag
        }
        
    return standardized_tags


async def find_problems_by_tag_names(
    session: AsyncSession,
    tag_names: List[str],
    skip: int = 0,
    limit: int = 100
) -> List[Problem]:
    """
    Find problems that match the given tag names.
    
    Args:
        session: Async database session
        tag_names: List of tag names to search for
        skip: Number of items to skip for pagination
        limit: Maximum number of items to return
        
    Returns:
        List of matching Problem instances
    """
    # Convert tag names to lowercase for consistency
    tag_names = [name.lower() for name in tag_names]
    
    # Query for problems with any of the given tags
    query = select(Problem).join(Problem.tags).where(
        Tag.name.in_(tag_names)
    ).offset(skip).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().unique().all()
