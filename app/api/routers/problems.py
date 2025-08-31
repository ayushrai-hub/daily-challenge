from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Body, Request
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.api import deps
from app.schemas.problem import ProblemCreate, ProblemRead, ProblemReadDetailed, ProblemUpdate
from app.repositories.problem import ProblemRepository
from app.db.models.user import User
from app.db.models.problem import ProblemStatus, VettingTier
from app.utils.markdown_utils import markdown_to_html, markdown_preview, get_markdown_css

router = APIRouter(
    prefix="/problems",
    tags=["problems"],
    dependencies=[Depends(deps.get_current_verified_user)],  # Apply verified user auth to all routes
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Email verification required"}}
)

@router.post("", response_model=ProblemRead)
async def create_problem(
    problem_in: ProblemCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can create problems
):
    """
    Create a new problem.
    """
    # Import logging utility
    from app.utils.logging_utils import log_admin_action
    
    # Log admin action
    log_admin_action(
        user=current_user,
        action="create_problem",
        problem_title=problem_in.title,
        difficulty=problem_in.difficulty
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.create(problem_in)
    return problem

@router.get("", response_model=List[ProblemRead])
async def read_problems(
    request: Request,
    skip: int = 0,
    limit: int = 500,
    # Filter parameters
    title: Optional[str] = Query(None, description="Filter by title (exact match)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    content_source_id: Optional[UUID] = Query(None, description="Filter by content source ID"),
    status: Optional[ProblemStatus] = Query(None, description="Filter by status (draft/approved/archived)"),
    created_at_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    created_at_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    tag_id: Optional[UUID] = Query(None, description="Filter problems by specific tag ID"),
    db: Session = Depends(deps.get_db),
    # For non-admins, require email verification to access problem listings
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Retrieve problems with optional filtering.
    
    Supports filtering by various attributes including:
    - title: Filter by problem title (exact match)
    - difficulty: Filter by difficulty level (easy, medium, hard)
    - content_source_id: Filter by source of the problem
    - status: Filter by status (draft/approved/archived)
    - created_at_before: Filter for problems created before specified datetime
    - created_at_after: Filter for problems created after specified datetime
    - tag_id: Filter for problems with specific tag
    """
    # Use the logging utility for user activity tracking
    from app.utils.logging_utils import log_user_activity
    
    # Log user activity with filters
    log_user_activity(
        user=current_user,
        action="read_problems",
        filters={
            "title": title,
            "difficulty": difficulty,
            "status": str(status) if status else None,
            "tag_id": str(tag_id) if tag_id else None,
            "skip": skip,
            "limit": limit
        }
    )
    
    problem_repo = ProblemRepository(db)
    
    # Debug output to help diagnose filtering issues
    print(f"DEBUG: Filtering problems with params: title={title}, difficulty={difficulty}, status={status}")
    
    # Build filter dictionary from provided parameters
    filters = {}
    if title is not None:
        # Use title__ilike for case-insensitive partial matching
        filters["title__ilike"] = f"%{title}%"
    if difficulty is not None:
        filters["difficulty"] = difficulty
    if content_source_id is not None:
        filters["content_source_id"] = content_source_id
    if status is not None:
        filters["status"] = status
        
    # Handle date range filters
    if created_at_before is not None:
        filters["created_at__lt"] = created_at_before
    if created_at_after is not None:
        filters["created_at__gt"] = created_at_after
        
    # Handle tag filtering (this might need special handling in the repository)
    if tag_id is not None:
        filters["tag_id"] = tag_id
    
    problems = problem_repo.get_multi(skip=skip, limit=limit, **filters)
    return problems

@router.get("/{problem_id}", response_model=ProblemRead)
async def read_problem(
    problem_id: UUID,
    db: Session = Depends(deps.get_db),
    # Require email verification for accessing individual problems
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Get problem by ID.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log user activity
    log_user_activity(
        user=current_user,
        action="read_problem",
        problem_id=str(problem_id)
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    return problem


@router.get("/{problem_id}/detailed", response_model=ProblemReadDetailed)
async def read_problem_detailed(
    problem_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Get problem by ID with detailed Markdown preview features.
    
    This endpoint returns the problem with additional Markdown rendering features,
    including rendered HTML, table of contents, and CSS for proper displaying.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log user activity
    log_user_activity(
        user=current_user,
        action="read_problem_detailed",
        problem_id=str(problem_id)
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
        
    preview_data = markdown_preview(problem.content)
    return {**problem.__dict__, **preview_data}


@router.get("/{problem_id}/markdown.css", response_class=Response)
async def get_markdown_css_for_problem(
    problem_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_verified_user)
):
    """
    Get CSS styles for Markdown rendering of problem content.
    
    This endpoint returns the CSS required to properly render Markdown content
    for problems, including code highlighting styles.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log user activity
    log_user_activity(
        user=current_user,
        action="get_markdown_css",
        problem_id=str(problem_id)
    )
    
    # First verify that the problem exists and user has access
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Return CSS with proper Content-Type
    css_content = get_markdown_css()
    return Response(
        content=css_content,
        media_type="text/css"
    )


# Define models for problem status updates
class ProblemStatusUpdate(BaseModel):
    """Request model for updating a problem's status"""
    status: ProblemStatus
    reviewer_notes: Optional[str] = None


class ProblemApprovalRequest(BaseModel):
    """Request model for approving a problem"""
    vetting_tier: Optional[VettingTier] = None  # Can optionally update vetting tier during approval
    reviewer_notes: Optional[str] = None


@router.put("/{problem_id}/status", response_model=ProblemRead)
async def update_problem_status(
    problem_id: UUID,
    status_update: ProblemStatusUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can update problem status
):
    """
    Update a problem's status (draft, approved, archived, pending).
    
    This endpoint allows administrators to change the status of a problem.
    When setting to 'approved', it also records the approval timestamp.
    """
    # Import logging utility
    from app.utils.logging_utils import log_admin_action
    
    # Log admin action
    log_admin_action(
        user=current_user,
        action="update_problem_status",
        problem_id=str(problem_id),
        new_status=str(status_update.status),
        has_reviewer_notes=bool(status_update.reviewer_notes)
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Update problem status with the current user as reviewer
    problem = problem_repo.update_status(
        problem_id=problem_id,
        new_status=status_update.status,
        reviewer_id=current_user.id
    )
    
    # Add reviewer notes if provided
    if status_update.reviewer_notes:
        if problem.problem_metadata is None:
            problem.problem_metadata = {}
        problem.problem_metadata["reviewer_notes"] = status_update.reviewer_notes
        db.add(problem)
        db.commit()
        db.refresh(problem)
    
    return problem


@router.post("/{problem_id}/approve", response_model=ProblemRead)
async def approve_problem(
    problem_id: UUID,
    request: Request,
    approval_request: ProblemApprovalRequest = Body(default=None),
    db: Session = Depends(deps.get_db),
    # Log admin user activity and ensure admin permissions in one dependency
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Approve a problem, marking it ready for delivery to users.
    
    This specialized endpoint handles the complete approval workflow:
    1. Updates the problem status to 'approved'
    2. Records the approval timestamp
    3. Optionally updates the vetting tier
    4. Records the admin who performed the approval
    """
    # Use the improved logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin approval action with problem details
    log_admin_action(
        user=current_user,
        action="approve_problem",
        problem_id=str(problem_id),
        tier=str(approval_request.vetting_tier) if approval_request and approval_request.vetting_tier else None,
        has_reviewer_notes=bool(approval_request and approval_request.reviewer_notes)
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # If already approved, return error
    if problem.status == ProblemStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem is already approved"
        )
    
    # Update vetting tier if specified
    if approval_request and approval_request.vetting_tier:
        problem.vetting_tier = approval_request.vetting_tier
    
    # Update problem status to approved
    problem = problem_repo.update_status(
        problem_id=problem_id,
        new_status=ProblemStatus.approved,
        reviewer_id=current_user.id
    )
    
    # Add reviewer notes if provided
    if approval_request and approval_request.reviewer_notes:
        if problem.problem_metadata is None:
            problem.problem_metadata = {}
        problem.problem_metadata["reviewer_notes"] = approval_request.reviewer_notes
        db.add(problem)
        db.commit()
        db.refresh(problem)
    
    return problem


@router.put("/{problem_id}", response_model=ProblemRead)
async def update_problem(
    problem_id: UUID,
    problem_update: ProblemUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Only admins can update problems
):
    """
    Update a problem's information.
    
    This endpoint allows updating various fields of a problem.
    """
    # Import logging utility
    from app.utils.logging_utils import log_admin_action
    
    # Log admin action
    log_admin_action(
        user=current_user,
        action="update_problem",
        problem_id=str(problem_id),
        fields_updated=str([k for k, v in problem_update.model_dump(exclude_unset=True).items()])
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Update problem using repository update method
    updated_problem = problem_repo.update(obj_in=problem_update, db_obj=problem)
    return updated_problem
