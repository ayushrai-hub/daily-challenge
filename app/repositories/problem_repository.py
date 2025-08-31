"""
Repository functions for creating problems with tags.
Extends the functionality of the core problem repository.
"""
from typing import Dict, List, Any, Optional, Union, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session  # Add synchronous Session for sync operations
from sqlalchemy.future import select
from sqlalchemy import func  # Add SQLAlchemy func for case-insensitive queries
from uuid import UUID

from app.db.models.problem import Problem, DifficultyLevel, VettingTier, ProblemStatus
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.core.logging import get_logger
from app.repositories.tag import TagRepository
from app.services.tag_normalizer import TagNormalizer
from app.services.tag_mapper import get_tag_mapper

logger = get_logger()

# Legacy tag mappings for backward compatibility
# This is defined at module level so it can be used across functions
TAG_MAPPING = {
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
    
    # Difficulty levels
    'easy': {'std_name': 'easy', 'parent': 'difficulty'},
    'medium': {'std_name': 'medium', 'parent': 'difficulty'},
    'hard': {'std_name': 'hard', 'parent': 'difficulty'},
}


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
        # Create a TagRepository to use async get_or_create methods
        from app.repositories.tag import TagRepository
        tag_repo = TagRepository(None)  # Session passed separately to async method
        
        # Process tags using case-insensitive get_or_create to avoid constraint violations
        problem_tags = []
        for tag_name in tag_names:
            try:
                # Use case-insensitive tag lookup/creation with the original case preserved
                tag = await tag_repo.get_or_create_case_insensitive_async(session, tag_name)
                problem_tags.append(tag)
                logger.info(f"Found/created tag: {tag.name} (ID: {tag.id})")
            except Exception as e:
                logger.error(f"Error getting or creating tag '{tag_name}': {str(e)}")
        
        # Replace the existing_tags with our safely created tags
        existing_tags = problem_tags
        
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
            - solution: Problem solution
            - difficulty_level: Problem difficulty level (enum)
            Optional fields:
            - tags: List of tag names to associate with the problem
            - status: Problem status (enum)
            - vetting_tier: Problem vetting tier (enum)
            - content_source_id: ID of the content source
            - approved_at: Approval timestamp
    
    Returns:
        UUID of the created problem
        
    Raises:
        ValueError: If required fields are missing
    """
    # Validate required fields
    required_fields = ["title", "description", "solution", "difficulty_level"]
    for field in required_fields:
        if field not in problem_data:
            raise ValueError(f"Required field '{field}' is missing")

    # Extract tag names if provided
    raw_tag_names = problem_data.get("tags", [])
    
    # Create tag repository for database operations
    tag_repo = TagRepository(db)
    
    # Initialize TagNormalizer for normalizing tag names
    tag_normalizer = TagNormalizer(tag_repo)
    
    # Log received tags
    logger.info(f"Processing tags for problem '{problem_data['title']}': {raw_tag_names}")
    
    # Step 1: Normalize tag names (capitalize first letter, consistent casing)
    normalized_tag_names = tag_normalizer.normalize_tag_names(raw_tag_names)
    logger.info(f"Normalized tags: {normalized_tag_names}")
    
    # Step 2: Standardize and organize tags into hierarchical categories
    standardized_tags = standardize_and_organize_tags(db, raw_tag_names)
    logger.info(f"Standardized tags: {standardized_tags}")
    
    # Collect the tag categories that need to be created first (parent tags)
    needed_parent_categories = set()
    parent_hierarchy = {}
    for tag_key, tag_info in standardized_tags.items():
        parent_category = tag_info.get('parent_category')
        if parent_category:
            needed_parent_categories.add(parent_category)
            parent_hierarchy[tag_key] = parent_category
    
    logger.info(f"Needed parent categories: {needed_parent_categories}")
    logger.info(f"Parent hierarchy: {parent_hierarchy}")
    
    # Step 3: Find existing parent categories in the database - don't create new ones
    # Store as a dictionary of dictionaries with 'obj', 'id', and 'name' keys to prevent session binding issues
    parent_category_tags = {}
    for category in needed_parent_categories:
        try:
            # IMPORTANT: Now we only look for existing tags without creating new ones
            logger.info(f"Looking for existing parent category tag: '{category}'")
            
            # Use only get_by_name methods to find existing tags without creating
            existing_parent = tag_repo.get_by_name_case_insensitive_safe(category)
            
            if existing_parent:
                # Extract important values before storing and convert to Python primitives
                parent_name = str(existing_parent.name) if existing_parent.name else ""
                parent_id = existing_parent.id  # UUID objects are safe across sessions
                logger.info(f"Found existing parent category: {parent_name} (ID: {parent_id})")
                
                # ONLY store primitive values, not the Tag object, to avoid session binding issues
                parent_category_tags[category] = {
                    'id': parent_id,
                    'name': parent_name
                }
                
                # Map the exact case version so future lookups will find it
                if str(category).lower() != parent_name.lower():
                    parent_category_tags[parent_name] = {
                        'id': parent_id,
                        'name': parent_name
                    }
            else:
                # Don't create missing categories - just log it for admin review
                logger.warning(f"Parent category '{category}' doesn't exist in the database - skipping")
                # Store category name in the metadata for later admin processing
        except Exception as e:
            logger.error(f"Error handling parent tag '{category}': {str(e)}")
            # If we can't create the parent, skip this tag relationship
            # but continue with the rest of the process
            logger.warning(f"Skipping parent tag relationship for '{category}'")
            continue
    
    # Process the standardized tags and collect tag names and IDs (NOT tag objects)
    # This avoids session binding issues by working with names and IDs instead of objects
    tag_names_to_use = []  # We'll store just the tag names and query them in one go later
    tag_ids_by_name = {}  # Store tag IDs by name for relationship creation
    for tag_key, tag_info in standardized_tags.items():
        # Check if we already have an existing tag ID from the standardization step
        if 'existing_tag_id' in tag_info:
            # We already identified an existing tag during standardization
            existing_tag_id = tag_info['existing_tag_id']
            tag_result = db.query(Tag.name, Tag.id).filter(Tag.id == existing_tag_id).first()
            if tag_result:
                tag_name = tag_result[0]
                tag_ids_by_name[tag_name] = existing_tag_id
            logger.info(f"Using pre-identified existing tag by ID: {tag_name} (ID: {existing_tag_id})")
            tag_names_to_use.append(tag_name)
            continue
        
        # If we don't have an existing tag ID, proceed with lookups
        # IMPORTANT: Only check if tags exist by name, don't try to get the actual objects
        try:
            canonical_name = None
            
            # First check if there's an original tag name for a more accurate lookup
            if 'original_tag' in tag_info:
                original_tag_name = tag_info.get('original_tag')
                # Check if this tag exists and get its canonical name
                if tag_repo.name_exists_case_insensitive(original_tag_name):
                    canonical_name = tag_repo.get_canonical_name(original_tag_name)
                    if canonical_name:
                        logger.info(f"Found existing tag using original name: '{original_tag_name}' -> '{canonical_name}'")
            
            # If not found by original name, try the standardized key
            if not canonical_name and tag_repo.name_exists_case_insensitive(tag_key):
                canonical_name = tag_repo.get_canonical_name(tag_key)
                if canonical_name:
                    logger.info(f"Found existing tag using standardized name: '{tag_key}' -> '{canonical_name}'")
            
            # If we found a canonical name, add it to our list and get its ID       
            if canonical_name:
                tag_names_to_use.append(canonical_name)
                # Get the ID for this canonical tag name
                tag_id_result = db.query(Tag.id).filter(func.lower(Tag.name) == func.lower(canonical_name)).first()
                if tag_id_result:
                    tag_ids_by_name[canonical_name] = tag_id_result[0]
            else:
                logger.warning(f"Tag '{tag_key}' doesn't exist in the database - skipping")
                # This tag will need to be created by the admin
                continue
                
        except Exception as e:
            logger.error(f"Error finding tag '{tag_key}': {str(e)}")
            # Skip this tag rather than failing the whole problem
            logger.warning(f"Skipping problematic tag '{tag_key}' due to error")
            continue
        
        # If the tag has a primary parent category, create the relationship in tag_hierarchy
        parent_category = tag_info.get('parent_category')
        # Get original or canonical tag name to look up its ID
        tag_name = tag_info.get('original_tag', tag_key)
        if canonical_name:
            tag_name = canonical_name
            
        # Only proceed if we have both parent and child tag IDs
        if parent_category and parent_category in parent_category_tags and tag_name in tag_ids_by_name:
            parent_tag_info = parent_category_tags[parent_category]
            child_tag_id = tag_ids_by_name[tag_name]
            
            # Access the pre-extracted parent tag ID
            parent_tag_id = parent_tag_info['id']
            
            # Check if relationship already exists
            existing_relationship = db.query(TagHierarchy).filter(
                TagHierarchy.parent_tag_id == parent_tag_id,
                TagHierarchy.child_tag_id == child_tag_id
            ).first()
            
            if not existing_relationship:
                # Create parent-child relationship
                child_parent = TagHierarchy(
                    parent_tag_id=parent_tag_id,
                    child_tag_id=child_tag_id
                )
                db.add(child_parent)
                logger.info(f"Created child parent tag relationship: {tag_name} (ID: {child_tag_id}) with parent: {parent_category} (ID: {parent_tag_id})")
        
        # If the tag has additional parents, create those relationships too
        additional_parents = tag_info.get('additional_parents', [])
        for add_parent in additional_parents:
            # Use case-insensitive lookup for additional parents too
            # First check if we already have this parent in our cache
            if add_parent in parent_category_tags:
                parent_tag_info = parent_category_tags[add_parent]
                # Use the pre-extracted values
                parent_tag_name = str(parent_tag_info['name']) if parent_tag_info['name'] else ""
                parent_tag_id = parent_tag_info['id']
                logger.info(f"Using cached parent tag for '{add_parent}': {parent_tag_name} (ID: {parent_tag_id})")
            else:
                try:
                    # IMPORTANT: First look for existing tag with case-insensitive match
                    existing_parent = tag_repo.get_by_name_case_insensitive_safe(add_parent)
                    
                    if existing_parent:
                        parent_tag = existing_parent
                        # Extract values to prevent session binding issues and convert to Python primitives
                        parent_tag_name = str(parent_tag.name) if parent_tag.name else ""
                        parent_tag_id = parent_tag.id
                        logger.info(f"Found existing additional parent tag: {parent_tag_name} (ID: {parent_tag_id}) for '{add_parent}'")
                        # Cache both the original name and the actual name for future lookups
                        # ONLY store primitive values, not the Tag object
                        parent_category_tags[add_parent] = {
                            'id': parent_tag_id,
                            'name': parent_tag_name
                        }
                        if str(add_parent).lower() != parent_tag_name.lower():
                            parent_category_tags[parent_tag_name] = {
                                'id': parent_tag_id,
                                'name': parent_tag_name
                            }
                    else:
                        # Only create if it doesn't exist
                        parent_tag = tag_repo.get_or_create_case_insensitive(add_parent)
                        # Extract values to prevent session binding issues
                        parent_tag_name = str(parent_tag.name) if parent_tag.name else ""
                        parent_tag_id = parent_tag.id
                        logger.info(f"Created new additional parent tag: {parent_tag_name} (ID: {parent_tag_id})")
                        parent_category_tags[add_parent] = {
                            'id': parent_tag_id,
                            'name': parent_tag_name
                        }
                except Exception as e:
                    logger.error(f"Error handling additional parent tag '{add_parent}': {str(e)}")
                    # Skip this relationship if there's an error
                    logger.warning(f"Skipping additional parent relationship for '{add_parent}'")
                    continue
            
            # Get child tag ID from our mapping
            if tag_name in tag_ids_by_name:
                child_tag_id = tag_ids_by_name[tag_name]
                
                # Get the parent tag ID from the info dictionary
                parent_tag_info = parent_category_tags[add_parent]
                parent_tag_id = parent_tag_info['id']
            
                # Check if relationship already exists
                existing_relationship = db.query(TagHierarchy).filter(
                    TagHierarchy.parent_tag_id == parent_tag_id,
                    TagHierarchy.child_tag_id == child_tag_id
                ).first()
                
                if not existing_relationship and parent_tag_id != child_tag_id:  # Avoid self-reference
                    # Create additional parent-child relationship
                    add_parent_rel = TagHierarchy(
                        parent_tag_id=parent_tag_id,
                        child_tag_id=child_tag_id
                    )
                    db.add(add_parent_rel)
                    logger.info(f"Added additional parent {add_parent} for tag {tag_name}")
    
    # Step 5: Create the problem with additional metadata field
    # Query for all needed tags in one database operation to avoid session binding issues
    if tag_names_to_use:
        logger.info(f"Fetching {len(tag_names_to_use)} tags for problem from database")
        # Query all needed tags in a single database operation
        problem_tags = db.query(Tag).filter(Tag.name.in_(tag_names_to_use)).all()
        logger.info(f"Found {len(problem_tags)} tags in database")
    else:
        problem_tags = []
        logger.info("No tags to attach to problem")
    
    # Create the problem with the tags from the current session
    problem = Problem(
        title=problem_data["title"],
        description=problem_data["description"],
        solution=problem_data["solution"],
        difficulty_level=problem_data["difficulty_level"],
        status=problem_data.get("status", ProblemStatus.draft),
        vetting_tier=problem_data.get("vetting_tier", VettingTier.tier3_needs_review),
        content_source_id=problem_data.get("content_source_id"),
        approved_at=problem_data.get("approved_at"),
        problem_metadata=problem_data.get("problem_metadata"),  # Store additional metadata including pending tags
        tags=problem_tags  # Now these are fetched from the current session
    )
    
    # Add the problem to the database
    db.add(problem)
    
    # Get ID right away
    db.flush()
    
    # Commit all changes
    db.commit()
    
    # Log success
    logger.info(f"Created problem '{problem_data['title']}' with ID {problem.id} (sync)")
    
    return problem.id


def standardize_and_organize_tags(db: Session, tag_names: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Standardize tags and organize them into hierarchical categories.
    Support multi-parent relationships through the tag_hierarchy table.
    
    Args:
        db: Database session
        tag_names: List of tag names to standardize and organize
        
    Returns:
        Dictionary mapping standardized tag names to their parent categories and metadata
    """
    # Initialize the tag mapper service
    tag_mapper = get_tag_mapper(db)
    tag_repo = TagRepository(db)
    normalizer = TagNormalizer(tag_repo)
    
    # Standardize tag names and assign parent categories
    result = {}
    
    for tag_name in tag_names:
        # Skip empty tags
        if not tag_name or not tag_name.strip():
            continue
            
        # Clean the tag name (remove extra spaces, etc.)
        clean_tag_name = tag_name.strip()
        
        # IMPROVEMENT: First, try to directly match to an existing tag with case-insensitive lookup
        # This prioritizes using existing tags over creating new ones
        existing_tag = tag_repo.get_by_name_case_insensitive(clean_tag_name)
        
        if existing_tag:
            # We found an existing tag with this name (case insensitive)
            # Use its exact name to maintain consistent casing
            final_name = existing_tag.name
            logger.info(f"Using existing tag '{existing_tag.name}' for '{clean_tag_name}' (direct case-insensitive match)")
            
            # For exact matches, no need to do further normalization
            if final_name not in result:
                result[final_name] = {
                    'parent_category': None,  # Will be determined from existing relationships
                    'original_tag': tag_name,
                    'additional_parents': [],
                    'existing_tag_id': str(existing_tag.id)  # Store the existing tag ID
                }
                
                # Get parent categories from existing tag relationships
                parent_tags = tag_repo.get_parent_tags(existing_tag.id)
                if parent_tags:
                    parent_names = [p.name for p in parent_tags]
                    result[final_name]['additional_parents'] = parent_names
                    logger.info(f"Using existing parent relationships for tag '{final_name}': {parent_names}")
            
            continue  # Skip further processing for existing tags
            
        # If no direct match found, proceed with normal tag normalization
        # First normalize the tag name using the TagNormalizer service
        normalized_tags = normalizer.normalize_tag_names([clean_tag_name])
        normalized_name = normalized_tags[0] if normalized_tags else clean_tag_name
        
        # Map to existing tags if possible (handles aliases like 'nodejs' -> 'Node.js')
        mapped_tags = normalizer.map_to_existing_tags([normalized_name])
        mapped_name = mapped_tags[0] if mapped_tags else normalized_name
        
        # Check if we have a mapping for this tag in the legacy system (for backward compatibility)
        tag_key = clean_tag_name.lower()
        legacy_parent = None
        
        # Determine the final tag name to use
        final_name = mapped_name
        if tag_key in TAG_MAPPING:
            std_name = TAG_MAPPING[tag_key]['std_name']
            legacy_parent = TAG_MAPPING[tag_key]['parent']
            
            # Use the mapped name from the normalizer if we have one,
            # otherwise fall back to the standard name from the mapping
            if mapped_name == normalized_name:  # If mapping didn't change the name
                final_name = std_name
        
        # Ensure the tag is in the result dictionary with default values
        if final_name not in result:
            result[final_name] = {
                'parent_category': legacy_parent,
                'original_tag': tag_name,
                'additional_parents': []
            }
        
        # Get additional parent categories from the tag mapper service
        additional_parents = tag_mapper.get_additional_parents(final_name)
        
        # Store additional parents for later use in multi-parent relationships
        result[final_name]['additional_parents'] = additional_parents
        
        # If no primary parent is set but we have additional parents, use the first one
        if result[final_name]['parent_category'] is None and additional_parents:
            result[final_name]['parent_category'] = additional_parents[0]
            
        logger.info(f"Standardized tag '{tag_name}' to '{final_name}' with parents: {result[final_name]['additional_parents']}")
        
    return result


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
