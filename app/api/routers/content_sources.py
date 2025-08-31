from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api import deps
from app.schemas.content_source import ContentSourceCreate, ContentSourceRead
from app.repositories.content_source import ContentSourceRepository
from app.db.models.content_source import SourcePlatform, ProcessingStatus
from app.db.models.user import User  # Added User model for logging

router = APIRouter(
    prefix="/content-sources",
    tags=["content_sources"]
)

@router.post("", response_model=ContentSourceRead)
async def create_content_source(
    content_source_in: ContentSourceCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)  # Add user for logging
) -> ContentSourceRead:
    """
    Create a new content source.
    
    Will check if a content source with the same platform and identifier already exists and
    return a 409 Conflict error if it does.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log content source creation attempt
    log_user_activity(
        user=current_user,
        action="create_content_source",
        platform=str(content_source_in.source_platform),
        title=content_source_in.source_title
    )
    
    content_source_repo = ContentSourceRepository(db)
    
    # Check for duplicate platform+identifier combination
    existing_source = content_source_repo.get_by_platform_and_identifier(
        platform=content_source_in.source_platform,
        source_identifier=content_source_in.source_identifier
    )
    if existing_source:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Content source with platform '{content_source_in.source_platform}' and "
                   f"identifier '{content_source_in.source_identifier}' already exists"
        )
    
    # Create the content source
    content_source = content_source_repo.create(content_source_in)
    return content_source

@router.get("", response_model=List[ContentSourceRead])
async def read_content_sources(
    skip: int = 0,
    limit: int = 100,
    # Filter parameters
    source_title: Optional[str] = Query(None, description="Filter by source title (partial match)"),
    source_platform: Optional[SourcePlatform] = Query(None, description="Filter by source platform"),
    processing_status: Optional[ProcessingStatus] = Query(None, description="Filter by processing status"),
    source_identifier: Optional[str] = Query(None, description="Filter by source identifier"),
    source_url: Optional[str] = Query(None, description="Filter by source URL (partial match)"),
    ingested_at_before: Optional[datetime] = Query(None, description="Filter by ingestion date before"),
    ingested_at_after: Optional[datetime] = Query(None, description="Filter by ingestion date after"),
    processed_at_before: Optional[datetime] = Query(None, description="Filter by processing date before"),
    processed_at_after: Optional[datetime] = Query(None, description="Filter by processing date after"),
    created_at_before: Optional[datetime] = Query(None, description="Filter by creation date before"),
    created_at_after: Optional[datetime] = Query(None, description="Filter by creation date after"),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Retrieve content sources with optional filtering.
    
    Supports filtering by various attributes including:
    - source_title: Filter by title (partial match)
    - source_platform: Filter by platform (stackoverflow, gh_issues, blog, etc.)
    - processing_status: Filter by status (pending, processed, failed)
    - source_identifier: Filter by source identifier
    - source_url: Filter by source URL (partial match)
    - ingested_at_before/after: Filter by ingestion date range
    - processed_at_before/after: Filter by processing date range
    - created_at_before/after: Filter by creation date range
    """
    content_source_repo = ContentSourceRepository(db)
    
    # Build filter dictionary from provided parameters
    filters = {}
    if source_title is not None:
        # Use ilike for case-insensitive partial matching
        filters["source_title__ilike"] = f"%{source_title}%"
    if source_platform is not None:
        filters["source_platform"] = source_platform
    if processing_status is not None:
        filters["processing_status"] = processing_status
    if source_identifier is not None:
        filters["source_identifier"] = source_identifier
    if source_url is not None:
        filters["source_url__ilike"] = f"%{source_url}%"
    
    # Handle date range filters
    if ingested_at_before is not None:
        filters["ingested_at__lt"] = ingested_at_before
    if ingested_at_after is not None:
        filters["ingested_at__gt"] = ingested_at_after
    if processed_at_before is not None:
        filters["processed_at__lt"] = processed_at_before
    if processed_at_after is not None:
        filters["processed_at__gt"] = processed_at_after
    if created_at_before is not None:
        filters["created_at__lt"] = created_at_before
    if created_at_after is not None:
        filters["created_at__gt"] = created_at_after
    
    content_sources = content_source_repo.get_multi(skip=skip, limit=limit, **filters)
    return content_sources

@router.get("/{content_source_id}", response_model=ContentSourceRead)
async def read_content_source(
    content_source_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)  # Add user for logging
):
    """
    Get content source by ID.
    """
    # Import logging utility
    from app.utils.logging_utils import log_user_activity
    
    # Log content source retrieval
    log_user_activity(
        user=current_user,
        action="view_content_source",
        content_source_id=str(content_source_id)
    )
    
    content_source_repo = ContentSourceRepository(db)
    content_source = content_source_repo.get(content_source_id)
    if not content_source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content source not found"
        )
    return content_source
