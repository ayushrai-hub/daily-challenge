"""
Tag Normalization API

This API provides endpoints for normalizing and mapping tag names to ensure proper hierarchical
relationships and consistent naming conventions across the application.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
import logging

from app.db.models.user import User

from app.api import deps
from app.services.tag_mapper import get_tag_mapper
from app.schemas.tag import TagRead

router = APIRouter(
    prefix="/tag-normalization",
    tags=["tag_normalization"]
)

logger = logging.getLogger(__name__)

@router.post("/map-or-create", response_model=List[TagRead])
async def map_or_create_tags(
    tag_names: List[str],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Maps a list of tag names to proper tags, creating them if they don't exist.
    
    This endpoint ensures all tags:
    1. Have proper capitalization (e.g., "javascript" -> "JavaScript")
    2. Are assigned to appropriate parent categories
    3. Have consistent naming across the application
    4. Are not duplicated with case variations
    
    Returns:
        List of normalized tags that can be associated with problems
    """
    try:
        # Get tag mapper service
        tag_mapper = get_tag_mapper(db)
        
        # Log the incoming tag names
        logger.info(f"Normalizing tag names: {tag_names}")
        
        # Map tag names to actual Tag objects (creating if needed)
        tags = tag_mapper.map_tag_names_to_tags(tag_names)
        
        # Convert to response models
        return [TagRead.model_validate(tag) for tag in tags]
    
    except Exception as e:
        logger.error(f"Error during tag normalization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to normalize tags: {str(e)}"
        )

@router.get("/normalize", response_model=Dict[str, str])
async def normalize_tag_names(
    names: List[str],
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)
):
    """
    Normalizes tag names without creating or modifying database records.
    
    This is useful for displaying normalized tag names in the UI without making
    any database changes. It follows the same normalization rules as map-or-create.
    
    Returns:
        Dictionary mapping original tag names to normalized versions
    """
    try:
        # Get tag mapper service
        tag_mapper = get_tag_mapper(db)
        
        # Normalize each tag name
        normalized = {name: tag_mapper.normalize_tag_name(name) for name in names}
        
        return normalized
    
    except Exception as e:
        logger.error(f"Error during tag name normalization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to normalize tag names: {str(e)}"
        )
