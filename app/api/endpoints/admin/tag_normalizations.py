"""
Admin endpoints for managing tag normalizations.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import or_, func
from app.services.tag_normalizer import TagNormalizer
from app.api.deps import get_db, get_current_admin_user
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus
from app.db.models.tag import Tag
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.user import User
from app.repositories.tag import TagRepository
from app.schemas.tag_normalization import (
    TagNormalizationRead, 
    TagNormalizationUpdate,
    TagNormalizationApprove,
    TagNormalizationsList
)
from app.core.logging import get_logger
from datetime import datetime
from app.utils.logging_utils import log_admin_action

logger = get_logger()
router = APIRouter()


@router.get("/", response_model=TagNormalizationsList)
async def list_tag_normalizations(
    status: Optional[TagReviewStatus] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    List tag normalizations with optional filtering by status.
    Only accessible to admins.
    """
    # Log admin action for viewing tag normalizations list
    log_admin_action(
        user=current_user,
        action="list_tag_normalizations",
        status_filter=str(status.value) if status else None,
        page=page,
        page_size=page_size
    )
    
    query = db.query(TagNormalization)
    
    # Filter by status if provided
    if status:
        query = query.filter(TagNormalization.review_status == status)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    normalizations = query.order_by(TagNormalization.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        "items": normalizations,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "pages": (total_count + page_size - 1) // page_size
    }


@router.get("/stats", response_model=Dict[str, Any])
async def get_tag_normalization_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get statistics about tag normalizations.
    Only accessible to admins.
    """
    # Query to get counts for different review statuses
    stats = db.query(
        func.count(TagNormalization.id).label("total"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.pending).label("pending"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.approved).label("approved"),
        func.count(TagNormalization.id).filter(TagNormalization.review_status == TagReviewStatus.rejected).label("rejected"),
        func.count(TagNormalization.id).filter(
            (TagNormalization.review_status == TagReviewStatus.approved) & 
            (TagNormalization.source == "ai_generated")
        ).label("auto_approved")
    ).one()
    
    # Convert to dictionary
    return {
        "total": stats.total,
        "pending": stats.pending,
        "approved": stats.approved,
        "rejected": stats.rejected,
        "auto_approved": stats.auto_approved
    }


@router.get("/{normalization_id}", response_model=TagNormalizationRead)
async def get_tag_normalization(
    normalization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get a specific tag normalization by ID.
    Only accessible to admins.
    """
    normalization = db.query(TagNormalization).filter(
        TagNormalization.id == normalization_id
    ).first()
    
    if not normalization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag normalization with ID {normalization_id} not found"
        )
        
    return normalization


@router.put("/{normalization_id}", response_model=TagNormalizationRead)
async def update_tag_normalization(
    normalization_id: UUID,
    update_data: TagNormalizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update a tag normalization.
    Only accessible to admins.
    """
    normalization = db.query(TagNormalization).filter(
        TagNormalization.id == normalization_id
    ).first()
    
    if not normalization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag normalization with ID {normalization_id} not found"
        )
    
    # Update fields
    if update_data.normalized_name is not None:
        normalization.normalized_name = update_data.normalized_name
    
    if update_data.description is not None:
        normalization.description = update_data.description
    
    if update_data.review_status is not None:
        normalization.review_status = update_data.review_status
    
    if update_data.admin_notes is not None:
        normalization.admin_notes = update_data.admin_notes
    
    # Set reviewer info
    normalization.reviewed_by = current_user.id
    normalization.reviewed_at = datetime.now()
    
    db.commit()
    db.refresh(normalization)
    
    return normalization


@router.post("/{normalization_id}/approve", response_model=TagNormalizationRead)
async def approve_tag_normalization(
    normalization_id: UUID,
    approval_data: TagNormalizationApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Approve a tag normalization and either map it to an existing tag or create a new tag.
    Also associates the newly approved tag with relevant existing problems.
    Only accessible to admins.
    """
    # Log admin action for approving tag normalization
    log_admin_action(
        user=current_user,
        action="approve_tag_normalization",
        normalization_id=str(normalization_id),
        map_to_existing=bool(approval_data.existing_tag_id),
        existing_tag_id=str(approval_data.existing_tag_id) if approval_data.existing_tag_id else None,
        new_tag_name=approval_data.tag_name if approval_data.tag_name else None
    )
    
    # Override the normalization_id in the approval data with the path parameter
    # This ensures consistency between the path and any ID in the request body
    approval_data.normalization_id = normalization_id
    
    normalization = db.query(TagNormalization).filter(
        TagNormalization.id == normalization_id
    ).first()
    
    if not normalization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag normalization with ID {normalization_id} not found"
        )
    
    tag_repo = TagRepository(db)
    
    # If the normalization is already approved, return it as is
    if normalization.review_status == TagReviewStatus.approved and normalization.approved_tag_id:
        logger.info(f"Tag normalization {normalization_id} is already approved")
        return normalization
    
    # First prepare the normalization for approval
    # Check if we're mapping to an existing tag
    existing_tag = None
    if approval_data.existing_tag_id:
        # Find the existing tag
        existing_tag = db.query(Tag).filter(Tag.id == approval_data.existing_tag_id).first()
        
        if not existing_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Existing tag with ID {approval_data.existing_tag_id} not found"
            )
        
        # Check for duplicates before mapping
        similar_tags = db.query(Tag).filter(
            func.lower(Tag.name) == func.lower(existing_tag.name),
            Tag.id != existing_tag.id
        ).all()
        
        if similar_tags:
            logger.warning(f"Found {len(similar_tags)} duplicate tags for '{existing_tag.name}'. Using ID {existing_tag.id}")
        
        # Map to the existing tag
        normalization.approved_tag_id = existing_tag.id
        logger.info(f"Mapping tag normalization {normalization_id} to existing tag {existing_tag.name} ({existing_tag.id})")
    else:
        # Prepare tag name - use provided name, normalization name, or original
        tag_name = (
            approval_data.tag_name or 
            normalization.normalized_name or 
            normalization.original_name
        )
        
        # Update the normalization with any settings from the approval data
        if approval_data.description:
            normalization.description = approval_data.description
        
        # Store parent tag IDs in the normalization for the repository method to use
        if approval_data.parent_tag_ids:
            normalization.parent_tag_ids = approval_data.parent_tag_ids
        
        # Update the normalized name if a different tag name was provided
        if approval_data.tag_name and approval_data.tag_name != normalization.normalized_name:
            normalization.normalized_name = approval_data.tag_name
    
    # Add any admin notes
    if approval_data.admin_notes:
        normalization.admin_notes = approval_data.admin_notes
    
    # Now call the repository method to handle the approval process
    # This will create the tag if needed and associate it with problems
    result = tag_repo.approve_tag_normalization(
        id=normalization_id, 
        reviewed_by=current_user.id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve tag normalization with ID {normalization_id}"
        )
    
    # The repository method returns a tuple of (normalization, tag)
    normalization, tag = result
    
    logger.info(f"Tag normalization {normalization_id} has been approved with tag ID {tag.id}")
    
    return normalization


class RejectRequest(BaseModel):
    admin_notes: Optional[str] = None

@router.post("/{normalization_id}/reject", response_model=TagNormalizationRead)
async def reject_tag_normalization(
    normalization_id: UUID,
    request: RejectRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Reject a tag normalization.
    Only accessible to admins.
    """
    normalization = db.query(TagNormalization).filter(
        TagNormalization.id == normalization_id
    ).first()
    
    if not normalization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag normalization with ID {normalization_id} not found"
        )
    
    # Update review status
    normalization.review_status = TagReviewStatus.rejected
    normalization.reviewed_by = current_user.id
    normalization.reviewed_at = datetime.now()
    
    # Add any admin notes
    if request and request.admin_notes:
        normalization.admin_notes = request.admin_notes
    
    db.commit()
    db.refresh(normalization)
    
    return normalization


@router.post("/bulk-approve", response_model=List[TagNormalizationRead])
async def bulk_approve_tag_normalizations(
    bulk_approval: List[TagNormalizationApprove],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Bulk approve multiple tag normalizations.
    Only accessible to admins.
    """
    # Log admin action for bulk approval of tag normalizations
    log_admin_action(
        user=current_user,
        action="bulk_approve_tag_normalizations",
        approval_count=len(bulk_approval) if bulk_approval else 0
    )
    
    if not bulk_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tag normalizations provided for bulk approval"
        )
    
    approved_normalizations = []
    tag_repo = TagRepository(db)
    
    for approval_data in bulk_approval:
        normalization_id = approval_data.normalization_id
        if not normalization_id:
            continue
            
        normalization = db.query(TagNormalization).filter(
            TagNormalization.id == normalization_id
        ).first()
        
        if not normalization:
            logger.warning(f"Tag normalization with ID {normalization_id} not found during bulk approval")
            continue
        
        # Check if we're mapping to an existing tag
        if approval_data.existing_tag_id:
            # Find the existing tag
            existing_tag = db.query(Tag).filter(Tag.id == approval_data.existing_tag_id).first()
            
            if not existing_tag:
                logger.warning(f"Existing tag with ID {approval_data.existing_tag_id} not found during bulk approval")
                continue
            
            # Map to the existing tag
            normalization.approved_tag_id = existing_tag.id
            
        else:
            # Create a new tag
            new_tag = Tag(
                name=approval_data.tag_name or normalization.normalized_name,
                description=approval_data.description or normalization.description,
                tag_type=approval_data.tag_type
            )
            
            db.add(new_tag)
            db.flush()  # Get the ID right away
            
            # Link to the new tag
            normalization.approved_tag_id = new_tag.id
            
            # Add parent relationships if provided
            if approval_data.parent_tag_ids:
                for parent_id in approval_data.parent_tag_ids:
                    parent_tag = db.query(Tag).filter(Tag.id == parent_id).first()
                    
                    if parent_tag:
                        # Create parent-child relationship
                        tag_hierarchy = TagHierarchy(
                            parent_tag_id=parent_id,
                            child_tag_id=new_tag.id
                        )
                        db.add(tag_hierarchy)
                        logger.info(f"Added parent relationship: {parent_tag.name} -> {new_tag.name}")
        
        # Update review status
        normalization.review_status = TagReviewStatus.approved
        normalization.reviewed_by = current_user.id
        normalization.reviewed_at = datetime.now()
        
        # Add any admin notes
        if approval_data.admin_notes:
            normalization.admin_notes = approval_data.admin_notes
            
        approved_normalizations.append(normalization)
    
    # Commit all changes at once for better performance
    db.commit()
    
    # Refresh all normalizations
    for norm in approved_normalizations:
        db.refresh(norm)
    
    return approved_normalizations


class BulkRejectRequest(BaseModel):
    normalization_ids: List[UUID]
    admin_notes: Optional[str] = None

@router.post("/bulk-reject", response_model=List[TagNormalizationRead])
async def bulk_reject_tag_normalizations(
    request: BulkRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Bulk reject multiple tag normalizations.
    Only accessible to admins.
    """
    if not request.normalization_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tag normalization IDs provided for bulk rejection"
        )
    
    # Find all normalizations to reject
    normalizations = db.query(TagNormalization).filter(
        TagNormalization.id.in_(request.normalization_ids)
    ).all()
    
    if not normalizations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="None of the provided tag normalization IDs were found"
        )
    
    # Update all normalizations
    for normalization in normalizations:
        normalization.review_status = TagReviewStatus.rejected
        normalization.reviewed_by = current_user.id
        normalization.reviewed_at = datetime.now()
        
        # Add any admin notes
        if request.admin_notes:
            normalization.admin_notes = request.admin_notes
    
    # Commit all changes at once
    db.commit()
    
    # Refresh all normalizations
    for norm in normalizations:
        db.refresh(norm)
    
    return normalizations


@router.get("/similar-tags/{tag_name}", response_model=List[Dict[str, Any]])
async def find_similar_tags(
    tag_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Find similar existing tags to help with tag normalization.
    Only accessible to admins.
    """
    tag_repo = TagRepository(db)
    
    # Get normalized version of the tag
    normalizer = TagNormalizer(tag_repo)
    normalized_names = normalizer.normalize_tag_names([tag_name])
    normalized_name = normalized_names[0] if normalized_names else tag_name
    
    # Find exact matches (case-insensitive)
    exact_matches = db.query(Tag).filter(func.lower(Tag.name) == func.lower(normalized_name)).all()
    
    # Find similar matches (containing the tag name or vice versa)
    similar_matches = db.query(Tag).filter(
        or_(
            Tag.name.ilike(f"%{normalized_name}%"),
            func.lower(normalized_name).contains(func.lower(Tag.name))
        )
    ).filter(
        ~Tag.id.in_([tag.id for tag in exact_matches])
    ).limit(10).all()
    
    # Prepare result
    results = []
    
    # Add exact matches first
    for tag in exact_matches:
        results.append({
            "id": str(tag.id),
            "name": tag.name,
            "description": tag.description,
            "match_type": "exact",
            "similarity": 1.0
        })
    
    # Add similar matches
    for tag in similar_matches:
        # Calculate simple similarity score based on length difference and common characters
        tag_lower = tag.name.lower()
        norm_lower = normalized_name.lower()
        
        # Common characters ratio
        common_chars = set(tag_lower).intersection(set(norm_lower))
        all_chars = set(tag_lower).union(set(norm_lower))
        char_similarity = len(common_chars) / len(all_chars) if all_chars else 0
        
        # Length similarity
        max_len = max(len(tag_lower), len(norm_lower))
        len_similarity = 1 - (abs(len(tag_lower) - len(norm_lower)) / max_len) if max_len > 0 else 0
        
        # Combined similarity score
        similarity = (char_similarity * 0.7) + (len_similarity * 0.3)
        
        # Only include reasonably similar tags
        if similarity >= 0.3:
            results.append({
                "id": str(tag.id),
                "name": tag.name,
                "description": tag.description,
                "match_type": "similar",
                "similarity": round(similarity, 2)
            })
    
    # Sort by similarity
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    return results
