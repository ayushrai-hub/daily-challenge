"""
Problem Tags API

This module provides endpoints for managing tags associated with problems.
It uses the TagMapper service to ensure proper tag normalization and hierarchical relationships.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from uuid import UUID

from app.api import deps
from app.schemas.tag import TagRead
from app.services.tag_mapper import get_tag_mapper
from app.repositories.problem import ProblemRepository
from app.db.models.user import User  # For user logging
from app.utils.logging_utils import log_admin_action  # For admin logging

router = APIRouter(
    prefix="/problems/{problem_id}/tags",
    tags=["problem_tags"]
)

logger = logging.getLogger(__name__)

@router.post("", response_model=List[TagRead])
async def add_tags_to_problem(
    problem_id: UUID,
    tag_names: List[str],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin for tag management
):
    """
    Add tags to a problem.
    
    If tags don't exist, they will be created with proper parent-child relationships.
    Similar tags will be merged to prevent duplicates.
    Only accessible to admins.
    """
    # Log admin action for adding tags to a problem
    log_admin_action(
        user=current_user,
        action="add_tags_to_problem",
        problem_id=str(problem_id),
        tag_count=len(tag_names),
        tag_names=str(tag_names)
    )
    # Get the problem repository and verify problem exists
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Get the tag mapper service
    tag_mapper = get_tag_mapper(db)
    
    # Map tag names to tag IDs (creating tags if needed)
    tag_ids = tag_mapper.map_tag_names_to_tag_ids(tag_names)
    
    # Get current tag IDs for this problem to avoid duplicates
    current_tag_ids = {tag.id for tag in problem.tags}
    
    # Add tags to the problem using the association table directly to avoid session binding issues
    from app.db.models import problem_tags
    for tag_id in tag_ids:
        if tag_id not in current_tag_ids:
            # Use direct SQL insert to avoid session binding issues
            stmt = problem_tags.insert().values(problem_id=problem_id, tag_id=tag_id)
            db.execute(stmt)
    
    db.commit()
    db.refresh(problem)  # Refresh to get updated tags
    
    # Return updated tags
    return [TagRead.model_validate(tag) for tag in problem.tags]

@router.get("", response_model=List[TagRead])
async def get_problem_tags(
    problem_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Get all tags associated with a problem.
    """
    # Import logging utility for user actions
    from app.utils.logging_utils import log_user_activity
    
    # Log user viewing problem tags - a lightweight operation so keep logging minimal
    log_user_activity(
        user=current_user,
        action="view_problem_tags",
        problem_id=str(problem_id)
    )
    # Get the problem repository and verify problem exists
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    return [TagRead.model_validate(tag) for tag in problem.tags]

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_problem(
    problem_id: UUID,
    tag_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin for removing tags
):
    """
    Remove a tag from a problem.
    Only accessible to admins.
    """
    # Log admin action for removing a tag from a problem
    log_admin_action(
        user=current_user,
        action="remove_tag_from_problem",
        problem_id=str(problem_id),
        tag_id=str(tag_id)
    )
    # Get the problem repository and verify problem exists
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Find the tag in the problem's tags
    tag_to_remove = next((tag for tag in problem.tags if tag.id == tag_id), None)
    
    if not tag_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not associated with this problem"
        )
    
    # Remove the tag from the problem
    problem.tags.remove(tag_to_remove)
    db.commit()
    
    return None
