from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Any
import re
import logging
from sqlalchemy import and_
from app.api import deps
from app.schemas.tag import TagCreate, TagUpdate, TagRead
from app.repositories.tag import TagRepository
from app.db.models.tag import Tag, TagType
from app.services.tag_mapper import get_tag_mapper
from pydantic import BaseModel
from typing import Dict, List, Optional as OptionalType
from app.db.models.user import User  # Added User model for logging

# Configure logging
logger = logging.getLogger(__name__)


# Define a model for creating tag relationships
class TagRelationshipCreate(BaseModel):
    parent_id: OptionalType[UUID] = None
    child_id: OptionalType[UUID] = None
    relationship_type: OptionalType[str] = "parent_child"

router = APIRouter(
    prefix="/tags",
    tags=["tags"]
)

@router.post("", response_model=TagRead, status_code=status.HTTP_200_OK)
async def create_tag(
    tag_in: TagCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)  # Add user for logging
):
    """
    Create a new tag with proper hierarchical relationships.
    
    This endpoint creates a new tag and intelligently assigns parent-child relationships
    based on the tag's name and characteristics. It handles both single-parent and
    multi-parent relationships, and normalizes tag names for consistency.
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log tag creation attempt with context
    log_user_activity(
        user=current_user,
        action="create_tag",
        tag_name=tag_in.name,
        tag_type=tag_in.tag_type,
        has_parent=bool(tag_in.parent_tag_id or tag_in.parent_ids)
    )
    
    try:
        # Get tag mapper and repository
        tag_mapper = get_tag_mapper(db)
        tag_repo = TagRepository(db)
        
        # Check if similar tag already exists
        existing_tag = tag_mapper.find_similar_tag(tag_in.name)
        if existing_tag:
            logger.info(f"Found similar existing tag: {existing_tag.name} for input: {tag_in.name}")
            
            # If the existing tag is found but parent_tag_id is specified, add the parent relationship
            if tag_in.parent_tag_id and tag_in.parent_tag_id not in [p.id for p in tag_repo.get_parent_tags(existing_tag.id)]:
                try:
                    tag_repo.add_parent_child_relationship(tag_in.parent_tag_id, existing_tag.id)
                    logger.info(f"Added parent relationship for existing tag: {existing_tag.name}")
                except ValueError as e:
                    logger.warning(f"Failed to add parent relationship: {str(e)}")
            
            # Return the existing tag with updated relationships
            children = tag_repo.get_child_tags(existing_tag.id)
            parents = tag_repo.get_parent_tags(existing_tag.id)
            
            result = TagRead.model_validate(existing_tag)
            result.child_ids = [child.id for child in children]
            result.parent_tag_ids = [parent.id for parent in parents]
            result.parent_tag_id = result.parent_tag_ids[0] if result.parent_tag_ids else None
            
            return result
        
        # Create the tag first without parent relationship
        logger.info(f"Creating new tag: {tag_in.name}")
        
        # Create basic tag with core properties
        tag = tag_mapper.get_or_create_tag(
            name=tag_in.name,
            description=tag_in.description,
            tag_type=tag_in.tag_type,
            is_featured=tag_in.is_featured,
            is_private=tag_in.is_private
        )
        
        # Add parent relationships
        # First handle the parent_tag_id for backward compatibility
        if tag_in.parent_tag_id:
            try:
                tag_repo.add_parent_child_relationship(tag_in.parent_tag_id, tag.id)
                logger.info(f"Added single parent relationship for tag {tag.name}")
            except ValueError as e:
                logger.warning(f"Failed to add parent relationship: {str(e)}")
        
        # Then handle any additional parent_ids specified
        if tag_in.parent_ids:
            for parent_id in tag_in.parent_ids:
                # Skip if it's the same as parent_tag_id which we already processed
                if parent_id != tag_in.parent_tag_id:
                    try:
                        tag_repo.add_parent_child_relationship(parent_id, tag.id)
                        logger.info(f"Added additional parent relationship for tag {tag.name}")
                    except ValueError as e:
                        logger.warning(f"Failed to add parent relationship: {str(e)}")
        
        # Get the updated tag relationships for the response
        children = tag_repo.get_child_tags(tag.id)
        parents = tag_repo.get_parent_tags(tag.id)
        
        # Create response model
        result = TagRead.model_validate(tag)
        result.child_ids = [child.id for child in children]
        result.parent_tag_ids = [parent.id for parent in parents]
        result.parent_tag_id = result.parent_tag_ids[0] if result.parent_tag_ids else None
        
        # Explicitly commit the transaction to ensure changes are persisted for API tests
        # This is necessary because the tag_mapper only flushes but doesn't commit
        db.commit()
        
        return result
    except HTTPException as e:
        # Re-raise HTTP exceptions with original status
        raise
    except Exception as e:
        logger.error(f"Error creating tag: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tag: {str(e)}"
        )

@router.get("", response_model=List[TagRead])
async def read_tags(
    skip: int = 0,
    limit: int = 1000,  # Increased limit to ensure all tags are returned in tests
    name: Optional[str] = None,
    description: Optional[str] = None,
    tag_type: Optional[str] = None,
    is_featured: Optional[bool] = None,
    is_private: Optional[bool] = None,
    parent_tag_id: Optional[UUID] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Retrieve tags with optional filtering.
    
    Parameters:
    - skip: Number of items to skip (pagination)
    - limit: Maximum number of items to return (pagination)
    - name: Filter by tag name (partial match)
    - description: Filter by description (partial match)
    - tag_type: Filter by tag type (e.g., "concept", "technology")
    - is_featured: Filter by featured status
    - is_private: Filter by private status
    - parent_tag_id: Filter by parent tag ID
    """
    try:
        # First get all tags matching the criteria
        query = db.query(Tag)
        
        # Apply filters
        if name is not None:
            query = query.filter(Tag.name.ilike(f"%{name}%"))
        if description is not None:
            query = query.filter(Tag.description.ilike(f"%{description}%"))
        if tag_type is not None:
            try:
                enum_tag_type = TagType(tag_type)
                query = query.filter(Tag.tag_type == enum_tag_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tag_type: {tag_type}. Must be one of: {[t.value for t in TagType]}"
                )
        if is_featured is not None:
            query = query.filter(Tag.is_featured == is_featured)
        if is_private is not None:
            query = query.filter(Tag.is_private == is_private)
        if parent_tag_id is not None:
            # Use the TagHierarchy junction table for parent_tag_id filtering
            from app.db.models.tag_hierarchy import TagHierarchy
            query = query.join(
                TagHierarchy,
                and_(TagHierarchy.child_tag_id == Tag.id, TagHierarchy.parent_tag_id == parent_tag_id)
            )
        
        # Apply pagination and get all matching tags
        tags = query.offset(skip).limit(limit).all()
        
        # Get all tag IDs for the parent-child lookup
        tag_ids = [tag.id for tag in tags]
        
        # Get all child tags that have parents in our result set using the tag_hierarchy table
        from app.db.models.tag_hierarchy import TagHierarchy
        
        # Query the tag_hierarchy table to find child relationships
        hierarchy_entries = db.query(TagHierarchy).filter(TagHierarchy.parent_tag_id.in_(tag_ids)).all()
        
        # Map parent_id to child_ids
        parent_to_children = {}
        for entry in hierarchy_entries:
            if entry.parent_tag_id not in parent_to_children:
                parent_to_children[entry.parent_tag_id] = []
            parent_to_children[entry.parent_tag_id].append(entry.child_tag_id)
        
        # Prepare response with children arrays
        result = []
        for tag in tags:
            children = parent_to_children.get(tag.id, [])
            print(f"Tag {tag.id} ({tag.name}) has children: {children}")
            
            # Get parent tags from the tag_hierarchy table
            from app.db.models.tag_hierarchy import TagHierarchy
            parent_entries = db.query(TagHierarchy).filter(TagHierarchy.child_tag_id == tag.id).all()
            parent_ids = [entry.parent_tag_id for entry in parent_entries]
            
            tag_model = TagRead(
                id=tag.id,
                name=tag.name,
                description=tag.description,
                tag_type=tag.tag_type,
                is_featured=tag.is_featured,
                is_private=tag.is_private,
                parent_tag_ids=parent_ids,  # Use the new parent_tag_ids field
                parent_tag_id=parent_ids[0] if parent_ids else None,  # For backward compatibility
                created_at=tag.created_at,
                updated_at=tag.updated_at,
                children=children
            )
            result.append(tag_model)
        
        return result
        
    except Exception as e:
        print(f"Error in read_tags: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/{tag_id}", response_model=TagRead)
async def read_tag(
    tag_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get tag by ID.
    """
    try:
        # Set up tag repository for hierarchy operations
        tag_repo = TagRepository(db)
        
        # Get tag from database
        tag = tag_repo.get(tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )
        
        # Get children and parents using the tag hierarchy
        children = tag_repo.get_child_tags(tag_id)
        parents = tag_repo.get_parent_tags(tag_id)
        
        # Get IDs for response
        children_ids = [child.id for child in children]
        parent_ids = [parent.id for parent in parents]
        
        logger.info(f"Tag {tag.id} ({tag.name}) has children: {children_ids} and parents: {parent_ids}")
        
        # Create the response model
        result = TagRead.model_validate(tag)
        
        # Add relationship data to response
        result.child_ids = children_ids
        
        # Include parent information in the response
        result.parent_tag_ids = parent_ids
        
        return result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions with the original details
        raise
    except Exception as e:
        print(f"Error in read_tag: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.put("/{tag_id}", response_model=TagRead)
async def update_tag(
    tag_id: UUID,
    tag_in: TagUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Update a tag, maintaining proper hierarchical relationships.
    
    This endpoint updates a tag and ensures that name normalization and proper
    parent-child relationships are maintained. If the update would create a duplicate
    tag, the existing tag is returned instead.
    """
    try:
        tag_repo = TagRepository(db)
        tag_mapper = get_tag_mapper(db)
        
        # Get the tag to update
        existing_tag = tag_repo.get(tag_id)
        if not existing_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )
            
        # Handle potential duplicates if name is being changed
        if tag_in.name and tag_in.name != existing_tag.name:
            # Check if a tag with the new name already exists
            existing_by_name = tag_repo.get_by_name_case_insensitive(tag_in.name)
            if existing_by_name and existing_by_name.id != tag_id:
                # Return the existing tag instead of creating a duplicate
                logger.info(f"Found existing tag '{existing_by_name.name}' similar to update target '{tag_in.name}'")
                return TagRead.model_validate(existing_by_name)
        
        # Update basic tag properties (excluding parent_tag_id)
        update_data = {}
        for field, value in tag_in.model_dump(exclude_unset=True).items():
            if field != "parent_tag_id":
                update_data[field] = value
        
        # Apply the updates
        updated_tag = tag_repo.update_tag(tag_id, update_data)
        
        # Handle parent relationship if specified
        if tag_in.parent_tag_id is not None:
            try:
                # Add new parent relationship
                tag_repo.add_parent_child_relationship(tag_in.parent_tag_id, tag_id)
                logger.info(f"Added parent relationship for tag '{updated_tag.name}'")
            except ValueError as e:
                # Catch cycle detection errors
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot add parent relationship: {str(e)}"
                )
        
        # Get the updated tag with its relationships
        children = tag_repo.get_child_tags(tag_id)
        parents = tag_repo.get_parent_tags(tag_id)
        
        # Create response model
        result = TagRead.model_validate(updated_tag)
        result.child_ids = [child.id for child in children]
        result.parent_tag_ids = [parent.id for parent in parents]
        
        return result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating tag: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tag: {str(e)}"
        )

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Add admin user for logging - this is a destructive operation
):
    """
    Delete a tag and its hierarchy relationships.
    
    This endpoint removes a tag and all its hierarchy relationships (both parent and child).
    If the tag has children, the operation will be rejected to prevent orphaning tags.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    try:
        tag_repo = TagRepository(db)
        
        # Get the tag before deletion to include in log
        tag = tag_repo.get(tag_id)
        if tag:
            # Log admin action with details about the tag being deleted
            log_admin_action(
                user=current_user,
                action="delete_tag",
                tag_id=str(tag_id),
                tag_name=tag.name,
                tag_type=tag.tag_type if hasattr(tag, 'tag_type') else None
            )
        
        # Get the tag to delete
        tag = tag_repo.get(tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )
        
        # Check if tag has children using the TagHierarchy junction table
        children = tag_repo.get_child_tags(tag_id)
        if children and len(children) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete a tag that has {len(children)} child tags. Remove child relationships first."
            )
        
        # Delete the tag (the repository implementation will handle hierarchy cleanup)
        success = tag_repo.delete(tag_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete tag"
            )
            
        logger.info(f"Successfully deleted tag {tag_id} ({tag.name})")
        return None
            
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error deleting tag: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tag: {str(e)}"
        )


# Define a simplified tag model for hierarchical representation
class TagHierarchyItem(BaseModel):
    id: UUID
    name: str
    parent_tag_ids: List[UUID] = []
    parent_names: Dict[UUID, str] = {}
    children: List[UUID] = []


@router.get("/hierarchy", response_model=List[TagHierarchyItem])
async def get_tag_hierarchy(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get all tags with their hierarchical relationships.
    
    This endpoint returns all tags with parent-child relationships,
    organized by parentage for easy hierarchical display. If no tags exist,
    a set of default tags will be created with proper hierarchical relationships.
    """
    try:
        logger.info("Fetching tag hierarchy...")
        
        # Get tag mapper service
        tag_mapper = get_tag_mapper(db)
        
        # Get all tags from the database
        tags = db.query(Tag).all()
        logger.info(f"Found {len(tags)} tags in database")
        
        # If no tags exist yet, initialize default categories and tags
        if len(tags) == 0:
            logger.info("No tags found, initializing tag hierarchy")
            
            # Create parent categories using the tag mapper
            parent_categories = tag_mapper.get_or_create_parent_categories()
            
            # Get tag repository for hierarchy operations
            tag_repo = TagRepository(db)
            
            # Add default tags under each category
            for category_name, category_tag in parent_categories.items():
                if category_name in tag_mapper.TAG_CATEGORIES:
                    for tag_name in tag_mapper.TAG_CATEGORIES[category_name][:5]:  # Add first 5 tags from each category
                        # Create the tag first without parent relationship
                        child_tag = tag_mapper.get_or_create_tag(name=tag_name)
                        
                        # Then establish the parent-child relationship using the hierarchy
                        try:
                            tag_repo.add_parent_child_relationship(category_tag.id, child_tag.id)
                            logger.debug(f"Added parent-child relationship: {category_name} -> {tag_name}")
                        except ValueError as e:
                            logger.warning(f"Failed to create tag hierarchy: {str(e)}")
                            continue
            
            # Refresh the tag list after creating defaults
            db.commit()
            tags = db.query(Tag).all()
            logger.info(f"Created default tag hierarchy with {len(tags)} tags")
            
            # Run a cleanup pass to merge any duplicates and normalize names
            merge_stats = tag_mapper.merge_duplicate_tags()
            logger.info(f"Tag cleanup results: {merge_stats}")
            
            # Refresh the tag list one more time
            tags = db.query(Tag).all()
        
        # Get tag repository for hierarchy operations
        tag_repo = TagRepository(db)
        
        # Query the tag_hierarchy table to build parent-child relationships
        from app.db.models.tag_hierarchy import TagHierarchy
        hierarchies = db.query(TagHierarchy).all()
        
        # Create parent-child map
        parent_child_map = {}
        for tag in tags:
            if tag.id not in parent_child_map:
                parent_child_map[tag.id] = []
        
        # Populate child IDs from actual hierarchy relationships
        for hierarchy in hierarchies:
            parent_id = hierarchy.parent_tag_id
            child_id = hierarchy.child_tag_id
            
            if parent_id not in parent_child_map:
                parent_child_map[parent_id] = []
            parent_child_map[parent_id].append(child_id)
        
        # Create mapping of tag IDs to their first parent's name for display purposes
        parent_name_map = {}
        for hierarchy in hierarchies:
            child_id = hierarchy.child_tag_id
            parent_id = hierarchy.parent_tag_id
            
            # Find the parent tag
            parent = next((t for t in tags if t.id == parent_id), None)
            if parent:
                # Use the first parent found for display purposes
                if child_id not in parent_name_map:
                    parent_name_map[child_id] = parent.name
        
        # Build parent map for each tag
        tag_parents = {}
        tag_parent_names = {}
        
        for hierarchy in hierarchies:
            child_id = hierarchy.child_tag_id
            parent_id = hierarchy.parent_tag_id
            
            # Initialize if not exists
            if child_id not in tag_parents:
                tag_parents[child_id] = []
                tag_parent_names[child_id] = {}
                
            # Add this parent
            tag_parents[child_id].append(parent_id)
            
            # Find parent name
            parent = next((t for t in tags if t.id == parent_id), None)
            if parent:
                tag_parent_names[child_id][parent_id] = parent.name
        
        # Convert to response format with proper hierarchy
        result = []
        for tag in tags:
            children = parent_child_map.get(tag.id, [])
            parent_ids = tag_parents.get(tag.id, [])
            parent_names = tag_parent_names.get(tag.id, {})
            
            result.append(TagHierarchyItem(
                id=tag.id,
                name=tag.name,
                parent_tag_ids=parent_ids,
                parent_names=parent_names,
                children=children
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error getting tag hierarchy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tag hierarchy: {str(e)}"
        )

class TagHierarchyUpdate(BaseModel):
    parent_tag_ids: List[UUID] = []


@router.get("/{tag_id}/hierarchy", response_model=Dict[str, List])
async def get_tag_hierarchy_by_id(
    tag_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get the hierarchy for a specific tag, including its parents and children.
    
    Returns a dictionary with two keys:
    - parents: List of parent tag objects
    - children: List of child tag objects
    """
    try:
        # Get tag repository for hierarchy operations
        tag_repo = TagRepository(db)
        
        # Check if tag exists
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with id {tag_id} not found"
            )
        
        # Get parent and child tags
        parents = tag_repo.get_parent_tags(tag_id)
        children = tag_repo.get_child_tags(tag_id)
        
        # Convert to dict representation
        return {
            "parents": [{
                "id": parent.id,
                "name": parent.name,
                "tag_type": parent.tag_type
            } for parent in parents],
            "children": [{
                "id": child.id,
                "name": child.name,
                "tag_type": child.tag_type
            } for child in children]
        }
    
    except Exception as e:
        logger.error(f"Error getting tag hierarchy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tag hierarchy: {str(e)}"
        )


@router.put("/{tag_id}/hierarchy", response_model=dict)
async def update_tag_hierarchy(
    tag_id: UUID,
    hierarchy_update: TagHierarchyUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Add admin user for logging - this modifies hierarchy
):
    """
    Update the parent relationships for a specific tag.
    
    This endpoint allows setting parent tags for a given tag.
    Existing parent relationships will be replaced with the new set.
    
    Returns the updated hierarchy with parents and children.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    try:
        # Log admin action with details about the hierarchy update
        log_admin_action(
            user=current_user,
            action="update_tag_hierarchy",
            tag_id=str(tag_id),
            parent_count=len(hierarchy_update.parent_tag_ids) if hierarchy_update.parent_tag_ids else 0,
            parent_ids=str([str(pid) for pid in hierarchy_update.parent_tag_ids]) if hierarchy_update.parent_tag_ids else "[]"
        )
        # Get tag repository for hierarchy operations
        tag_repo = TagRepository(db)
        
        # Check if tag exists
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with id {tag_id} not found"
            )
            
        # Get current parent relationships
        current_parents = tag_repo.get_parent_tags(tag_id)
        current_parent_ids = [p.id for p in current_parents]
        
        # Remove parent relationships no longer needed
        for parent_id in current_parent_ids:
            if parent_id not in hierarchy_update.parent_tag_ids:
                tag_repo.remove_parent_child_relationship(parent_id, tag_id)
                logger.info(f"Removed parent relationship: {parent_id} -> {tag_id}")
        
        # Add new parent relationships
        for parent_id in hierarchy_update.parent_tag_ids:
            if parent_id not in current_parent_ids:
                try:
                    # Check if parent tag exists
                    parent_tag = db.query(Tag).filter(Tag.id == parent_id).first()
                    if not parent_tag:
                        logger.warning(f"Parent tag {parent_id} not found, skipping")
                        continue
                        
                    # Add relationship if it doesn't create a circular reference
                    tag_repo.add_parent_child_relationship(parent_id, tag_id)
                    logger.info(f"Added parent relationship: {parent_id} -> {tag_id}")
                except ValueError as e:
                    logger.warning(f"Failed to add parent relationship: {str(e)}")
        
        # Get updated parent and child tags
        updated_parents = tag_repo.get_parent_tags(tag_id)
        children = tag_repo.get_child_tags(tag_id)
        
        # Convert to dict representation
        return {
            "parents": [{
                "id": parent.id,
                "name": parent.name,
                "tag_type": parent.tag_type
            } for parent in updated_parents],
            "children": [{
                "id": child.id,
                "name": child.name,
                "tag_type": child.tag_type
            } for child in children]
        }
    
    except Exception as e:
        logger.error(f"Error updating tag hierarchy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tag hierarchy: {str(e)}"
        )


@router.post("/hierarchy/relationship", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_hierarchy_relationship(
    relationship: TagRelationshipCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Create a new parent-child relationship between two tags.
    
    This endpoint creates a direct relationship between a parent tag and a child tag.
    It validates the relationship to ensure it won't create a cycle in the hierarchy.
    
    At least one of parent_id or child_id must be provided.
    
    Returns the created relationship information.
    """
    try:
        # Validate that at least one of parent_id or child_id is provided
        if not relationship.parent_id and not relationship.child_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one tag (parent or child) must be specified"
            )
            
        # Get tag repository for hierarchy operations
        tag_repo = TagRepository(db)
        
        # If both parent and child are specified, create a direct relationship
        if relationship.parent_id and relationship.child_id:
            # Verify both tags exist
            parent_tag = db.query(Tag).filter(Tag.id == relationship.parent_id).first()
            child_tag = db.query(Tag).filter(Tag.id == relationship.child_id).first()
            
            if not parent_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent tag with id {relationship.parent_id} not found"
                )
                
            if not child_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child tag with id {relationship.child_id} not found"
                )
            
            # Check for circular reference
            if TagHierarchy.check_for_cycle(db, relationship.parent_id, relationship.child_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Creating this relationship would create a circular reference in the tag hierarchy"
                )
                
            # Create the relationship
            try:
                tag_repo.add_parent_child_relationship(
                    relationship.parent_id, 
                    relationship.child_id,
                    relationship_type=relationship.relationship_type
                )
                logger.info(f"Created parent-child relationship: {relationship.parent_id} -> {relationship.child_id}")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
                
            # Return the updated relationship info
            return {
                "status": "success",
                "message": "Parent-child relationship created successfully",
                "relationship": {
                    "parent_id": relationship.parent_id,
                    "parent_name": parent_tag.name,
                    "child_id": relationship.child_id,
                    "child_name": child_tag.name,
                    "relationship_type": relationship.relationship_type
                }
            }
        
        # For parent-only or child-only cases (these are placeholders for future expansion)
        # Frontend should handle most of the virtual visualizations for these cases
        elif relationship.parent_id:
            # Placeholder for parent-only case
            parent_tag = db.query(Tag).filter(Tag.id == relationship.parent_id).first()
            if not parent_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent tag with id {relationship.parent_id} not found"
                )
            
            return {
                "status": "success",
                "message": "Parent tag registered successfully",
                "relationship": {
                    "parent_id": relationship.parent_id,
                    "parent_name": parent_tag.name,
                    "relationship_type": relationship.relationship_type
                }
            }
            
        elif relationship.child_id:
            # Placeholder for child-only case
            child_tag = db.query(Tag).filter(Tag.id == relationship.child_id).first()
            if not child_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child tag with id {relationship.child_id} not found"
                )
            
            return {
                "status": "success",
                "message": "Child tag registered successfully",
                "relationship": {
                    "child_id": relationship.child_id,
                    "child_name": child_tag.name,
                    "relationship_type": relationship.relationship_type
                }
            }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating tag relationship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tag relationship: {str(e)}"
        )
