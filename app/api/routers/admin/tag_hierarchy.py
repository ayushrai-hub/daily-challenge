"""
Admin-specific tag hierarchy endpoints for advanced management capabilities.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
import logging

from app.api import deps
from app.repositories.tag import TagRepository
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.user import User
from app.utils.logging_utils import log_admin_action

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["admin", "tags"],
    dependencies=[Depends(deps.get_current_admin_user)]  # Enforce admin authentication on all routes
)


@router.get("", response_model=List[Dict[str, Any]])
async def get_admin_tag_hierarchy(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Explicitly get the admin user for logging
):
    """
    Get all tag hierarchy relationships for admin management.
    
    This endpoint returns all tag hierarchy relationships in the system.
    """
    # Log admin action for viewing tag hierarchy
    log_admin_action(
        user=current_user,
        action="view_tag_hierarchy"
    )
    
    try:
        # Get all tag hierarchy relationships
        hierarchy_relationships = db.query(TagHierarchy).all()
        
        # Convert to dict for API response
        result = []
        for relationship in hierarchy_relationships:
            # Get parent and child tag names for better usability
            parent_tag = db.query(Tag).filter(Tag.id == relationship.parent_tag_id).first()
            child_tag = db.query(Tag).filter(Tag.id == relationship.child_tag_id).first()
            
            result.append({
                "parent_tag_id": relationship.parent_tag_id,
                "parent_tag_name": parent_tag.name if parent_tag else None,
                "child_tag_id": relationship.child_tag_id,
                "child_tag_name": child_tag.name if child_tag else None,
                "relationship_type": relationship.relationship_type,
                "created_at": relationship.created_at
            })
        
        return result
    
    except Exception as e:
        logger.error(f"Error fetching tag hierarchy: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tag hierarchy: {str(e)}"
        )


@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_admin_tag_relationship(
    relationship: Dict[str, Any],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Explicitly get the admin user for logging
):
    """
    Create a new parent-child relationship between tags (admin endpoint).
    
    This admin endpoint forwards to the main tag hierarchy relationship creation endpoint
    with additional admin-specific processing and response format.
    """
    # Validate input
    parent_tag_id = relationship.get("parent_tag_id")
    child_tag_id = relationship.get("child_tag_id")
    relationship_type = relationship.get("relationship_type", "parent_child")
    
    # Log admin action for creating tag relationship
    log_admin_action(
        user=current_user,
        action="create_tag_relationship",
        parent_tag_id=str(parent_tag_id) if parent_tag_id else None,
        child_tag_id=str(child_tag_id) if child_tag_id else None,
        relationship_type=relationship_type
    )
    
    try:
        
        # Validate at least one ID is present
        if not parent_tag_id and not child_tag_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one tag (parent or child) must be specified"
            )
        
        # Get tag repository
        tag_repo = TagRepository(db)
        
        # Create the relationship if both tags are specified
        if parent_tag_id and child_tag_id:
            # Verify both tags exist
            parent_tag = db.query(Tag).filter(Tag.id == parent_tag_id).first()
            child_tag = db.query(Tag).filter(Tag.id == child_tag_id).first()
            
            if not parent_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent tag with id {parent_tag_id} not found"
                )
                
            if not child_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child tag with id {child_tag_id} not found"
                )
            
            # Check for circular reference with enhanced error reporting
            if TagHierarchy.check_for_cycle(db, parent_tag_id, child_tag_id):
                # Get tag names for better error reporting
                parent_tag_name = parent_tag.name if parent_tag else "Unknown"
                child_tag_name = child_tag.name if child_tag else "Unknown"
                
                # Find cycle path for improved debugging
                cycle_path = tag_repo.find_cycle_path(parent_tag_id, child_tag_id)
                path_info = ""
                if cycle_path and len(cycle_path) > 0:
                    path_names = []
                    for tag_id in cycle_path:
                        tag = db.query(Tag).filter(Tag.id == tag_id).first()
                        path_names.append(tag.name if tag else "Unknown")
                    path_info = f" Cycle path: {' → '.join(path_names)}"
                
                # Check for direct cycle (reverse relationship)
                direct_cycle = db.query(TagHierarchy).filter(
                    TagHierarchy.parent_tag_id == child_tag_id,
                    TagHierarchy.child_tag_id == parent_tag_id
                ).first() is not None
                
                error_message = ""
                if direct_cycle:
                    error_message = f"Cannot create this relationship as '{child_tag_name}' is already a parent of '{parent_tag_name}'."
                elif parent_tag_id == child_tag_id:
                    error_message = f"Cannot create a relationship where '{parent_tag_name}' is both parent and child (self-reference)."
                else:
                    error_message = f"Creating this relationship would create a circular reference in the tag hierarchy.{path_info}"
                
                log_admin_action(
                    user=current_user,
                    action="cycle_detected",
                    parent_tag_id=str(parent_tag_id),
                    parent_tag_name=parent_tag_name,
                    child_tag_id=str(child_tag_id),
                    child_tag_name=child_tag_name,
                    cycle_path=path_info,
                    error_message=error_message
                )
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
                
            # Create the relationship
            try:
                tag_repo.add_parent_child_relationship(
                    parent_tag_id, 
                    child_tag_id,
                    relationship_type=relationship_type
                )
                logger.info(f"Created parent-child relationship: {parent_tag_id} -> {child_tag_id}")
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
                    "parent_tag_id": parent_tag_id,
                    "parent_name": parent_tag.name,
                    "child_tag_id": child_tag_id,
                    "child_name": child_tag.name,
                    "relationship_type": relationship_type
                }
            }
        
        # Handle single tag cases (placeholders for admin UI)
        elif parent_tag_id:
            parent_tag = db.query(Tag).filter(Tag.id == parent_tag_id).first()
            if not parent_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent tag with id {parent_tag_id} not found"
                )
            
            return {
                "status": "success",
                "message": "Parent tag registered successfully",
                "relationship": {
                    "parent_tag_id": parent_tag_id,
                    "parent_name": parent_tag.name,
                    "relationship_type": relationship_type
                }
            }
            
        elif child_tag_id:
            child_tag = db.query(Tag).filter(Tag.id == child_tag_id).first()
            if not child_tag:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Child tag with id {child_tag_id} not found"
                )
            
            return {
                "status": "success",
                "message": "Child tag registered successfully",
                "relationship": {
                    "child_tag_id": child_tag_id,
                    "child_name": child_tag.name,
                    "relationship_type": relationship_type
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


@router.delete("/{parent_id}/{child_id}", response_model=Dict[str, Any])
async def remove_admin_tag_relationship(
    parent_id: UUID,
    child_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Explicitly get the admin user for logging
):
    """
    Remove a parent-child relationship between tags (admin endpoint).
    
    This admin endpoint allows removing a specific relationship by parent and child IDs.
    """
    # Log admin action for removing tag relationship (this is a destructive operation)
    log_admin_action(
        user=current_user,
        action="remove_tag_relationship",
        parent_tag_id=str(parent_id),
        child_tag_id=str(child_id)
    )
    
    try:
        # Get tag repository
        tag_repo = TagRepository(db)
        
        # Check if relationship exists
        relationship = db.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == parent_id,
            TagHierarchy.child_tag_id == child_id
        ).first()
        
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship between parent {parent_id} and child {child_id} not found"
            )
        
        # Remove the relationship
        tag_repo.remove_parent_child_relationship(parent_id, child_id)
        logger.info(f"Removed parent-child relationship: {parent_id} -> {child_id}")
        
        return {
            "status": "success",
            "message": "Relationship removed successfully"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error removing tag relationship: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing tag relationship: {str(e)}"
        )
