from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from sqlalchemy.orm import Session
from typing import List
import logging

from app.api import deps
from app.schemas.delivery_log import DeliveryLogCreate, DeliveryLogRead
from app.repositories.delivery_log import DeliveryLogRepository
from app.db.models.user import User  # For user context in logging
from app.utils.logging_utils import log_admin_action

router = APIRouter(
    prefix="/delivery-logs",
    tags=["delivery_logs"]
)

@router.post("", response_model=DeliveryLogRead)
async def create_delivery_log(
    delivery_log_in: DeliveryLogCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin for creating delivery logs
):
    """
    Create a new delivery log.
    Only accessible to admins.
    """
    # Log admin action for creating a delivery log
    log_admin_action(
        user=current_user,
        action="create_delivery_log",
        user_id=str(delivery_log_in.user_id),
        problem_id=str(delivery_log_in.problem_id) if delivery_log_in.problem_id else None
    )
    
    delivery_log_repo = DeliveryLogRepository(db)
    delivery_log = delivery_log_repo.create(delivery_log_in)
    return delivery_log

@router.get("", response_model=List[DeliveryLogRead])
async def read_delivery_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin for viewing delivery logs
):
    """
    Retrieve delivery logs.
    Only accessible to admins.
    """
    # Log admin action for viewing delivery logs list
    log_admin_action(
        user=current_user,
        action="view_delivery_logs",
        skip=skip,
        limit=limit
    )
    
    delivery_log_repo = DeliveryLogRepository(db)
    delivery_logs = delivery_log_repo.get_multi(skip=skip, limit=limit)
    return delivery_logs

@router.get("/{delivery_log_id}", response_model=DeliveryLogRead)
async def read_delivery_log(
    delivery_log_id: UUID,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_admin_user)  # Require admin for viewing specific delivery logs
):
    """
    Get delivery log by ID.
    Only accessible to admins.
    """
    # Log admin action for viewing a specific delivery log
    log_admin_action(
        user=current_user,
        action="view_delivery_log_detail",
        delivery_log_id=str(delivery_log_id)
    )
    
    delivery_log_repo = DeliveryLogRepository(db)
    delivery_log = delivery_log_repo.get(delivery_log_id)
    if not delivery_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery log not found"
        )
    return delivery_log
