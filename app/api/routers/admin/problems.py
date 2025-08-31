from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.api import deps
from app.schemas.problem import ProblemCreate, ProblemRead, ProblemReadDetailed, ProblemUpdate
from app.repositories.problem import ProblemRepository
from app.db.models.user import User
from app.db.models.problem import ProblemStatus, VettingTier
from app.utils.markdown_utils import markdown_to_html, markdown_preview, get_markdown_css

router = APIRouter(
    prefix="/problems", 
    tags=["admin-problems"],
    dependencies=[Depends(deps.get_current_admin_user)],  # Only admins can access these routes
    responses={
        401: {"description": "Unauthorized"}, 
        403: {"description": "Admin privileges required"},
        404: {"description": "Problem not found"}
    }
)

@router.get("", response_model=List[ProblemRead])
async def get_admin_problems(
    response: Response,
    skip: int = 0,
    limit: int = 1000,  # Higher limit for admin view
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    # Filter parameters
    search: Optional[str] = Query(None, description="Search across title and description"),
    title: Optional[str] = Query(None, description="Filter by title (partial match)"),
    status: Optional[ProblemStatus] = Query(None, description="Filter by status (draft/approved/archived/pending)"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    vetting_tier: Optional[VettingTier] = Query(None, description="Filter by vetting tier"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Admin only
):
    """
    Admin endpoint to retrieve all problems with pagination, sorting, and filtering.
    
    Returns problems ordered from newest to oldest (by creation date).
    
    Features:
    - Pagination with page and page_size parameters
    - Total count header for client-side pagination
    - Sorting by created_at in descending order (newest first)
    - Filtering by various attributes
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log admin accessing problem list with filter parameters
    log_admin_action(
        user=current_user,
        action="view_admin_problems",
        search_term=search,
        status_filter=str(status.value) if status else None,
        page=page,
        page_size=page_size
    )
    
    problem_repo = ProblemRepository(db)
    
    # Use page and page_size for pagination
    if page and page_size:
        skip = (page - 1) * page_size
        limit = page_size
    
    # Build filter dictionary from provided parameters
    filters = {}
    
    # Search across title
    if search is not None:
        filters["title__ilike"] = f"%{search}%"
    
    # Direct title filter
    if title is not None:
        filters["title__ilike"] = f"%{title}%"
    
    # Status filter
    if status is not None:
        # For string-based filtering, use status.value instead of enum object
        # This should work better with the SQLAlchemy filter system
        status_value = status.value if isinstance(status, ProblemStatus) else status
        filters["status"] = status_value
        print(f"DEBUG: Filtering problems with status: {status_value} (original: {status})")
    
    # Difficulty filter
    if difficulty is not None:
        filters["difficulty"] = difficulty
    
    # Vetting tier filter
    if vetting_tier is not None:
        filters["vetting_tier"] = vetting_tier
    
    # Get total count first (without pagination)
    # The count method accepts a different filter format than get_multi
    count_filters = {}
    
    # Convert advanced filters to simple filters for count()
    for k, v in filters.items():
        if "__" in k:
            # Skip advanced filters for count
            continue
        count_filters[k] = v
    
    print(f"DEBUG: Count filters: {count_filters}")
    total_count = problem_repo.count(count_filters)
    
    # Set total count header for frontend pagination
    response.headers["X-Total-Count"] = str(total_count)
    
    # Get paginated results with order_by
    try:
        print(f"DEBUG: Filtering problems with params: {filters}")
        problems = problem_repo.get_multi(
            skip=skip, 
            limit=limit, 
            order_by="created_at", 
            order_direction="desc",  # Newest first
            **filters
        )
        return problems
    except Exception as e:
        import traceback
        print(f"ERROR in admin problems endpoint: {str(e)}")
        print(traceback.format_exc())
        # Return empty list instead of 500 error to allow frontend to continue functioning
        return []


@router.get("/{problem_id}", response_model=ProblemReadDetailed)
async def get_admin_problem_detail(
    problem_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to get detailed problem information by ID.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log this admin action - viewing problem details is an important access event
    log_admin_action(
        user=current_user,
        action="view_problem_detail",
        problem_id=str(problem_id)
    )
    
    problem_repo = ProblemRepository(db)
    problem = problem_repo.get(problem_id)
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Convert to schema with detailed rendering
    detailed_problem = ProblemReadDetailed.from_orm(problem)
    
    # Add rendered HTML content if available
    if problem.content:
        html_content, toc = markdown_to_html(problem.content)
        detailed_problem.rendered_content = html_content
        detailed_problem.table_of_contents = toc
    
    return detailed_problem


@router.post("/{problem_id}/status", response_model=ProblemRead)
async def update_problem_status(
    problem_id: UUID,
    status: ProblemStatus,
    reviewer_notes: Optional[str] = None,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to update a problem's status (draft, approved, archived, pending).
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Log the admin action with detailed context
    log_admin_action(
        user=current_user,
        action="update_problem_status",
        problem_id=str(problem_id),
        new_status=str(status.value) if hasattr(status, "value") else str(status),
        has_reviewer_notes=bool(reviewer_notes)
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
        new_status=status,
        reviewer_id=current_user.id
    )
    
    # Add reviewer notes if provided
    if reviewer_notes:
        if problem.problem_metadata is None:
            problem.problem_metadata = {}
        problem.problem_metadata["reviewer_notes"] = reviewer_notes
        db.add(problem)
        db.commit()
        db.refresh(problem)
    
    return problem


@router.put("/{problem_id}", response_model=ProblemRead)
async def update_admin_problem(
    problem_id: UUID,
    problem_update: ProblemUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Admin endpoint to update a problem's information.
    """
    # Import logging utility for admin actions
    from app.utils.logging_utils import log_admin_action
    
    # Get fields being updated for audit trail
    updated_fields = [k for k, v in problem_update.dict(exclude_unset=True).items()]
    
    # Log the admin action with context about what's being changed
    log_admin_action(
        user=current_user,
        action="update_admin_problem",
        problem_id=str(problem_id),
        fields_updated=str(updated_fields),
        update_count=len(updated_fields)
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
