from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import select, func

from app.db.models.delivery_log import DeliveryLog, DeliveryStatus
from app.schemas.delivery_log import DeliveryLogCreate, DeliveryLogUpdate
from app.repositories.base import BaseRepository


class DeliveryLogRepository(BaseRepository[DeliveryLog, DeliveryLogCreate, DeliveryLogUpdate]):
    """Repository for DeliveryLog model providing CRUD operations and delivery log-specific queries."""
    
    def __init__(self, db: Session):
        super().__init__(model=DeliveryLog, db=db)
    
    def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 100) -> List[DeliveryLog]:
        """
        Get delivery logs for a specific user.
        
        Args:
            user_id: User ID to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of DeliveryLog instances
        """
        return self.db.query(DeliveryLog).filter(
            DeliveryLog.user_id == user_id
        ).order_by(DeliveryLog.delivered_at.desc()).offset(skip).limit(limit).all()
    
    def get_by_problem(self, problem_id: UUID, skip: int = 0, limit: int = 100) -> List[DeliveryLog]:
        """
        Get delivery logs for a specific problem.
        
        Args:
            problem_id: Problem ID to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of DeliveryLog instances
        """
        return self.db.query(DeliveryLog).filter(
            DeliveryLog.problem_id == problem_id
        ).order_by(DeliveryLog.delivered_at.desc()).offset(skip).limit(limit).all()
    
    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[DeliveryLog]:
        """
        Get delivery logs by status.
        
        Args:
            status: Status to filter by (e.g., 'delivered', 'failed')
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of DeliveryLog instances
        """
        return self.db.query(DeliveryLog).filter(
            DeliveryLog.status == status
        ).order_by(DeliveryLog.delivered_at.desc()).offset(skip).limit(limit).all()
    
    def get_by_date_range(self, start_date: datetime, end_date: datetime, skip: int = 0, limit: int = 100) -> List[DeliveryLog]:
        """
        Get delivery logs within a date range.
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of DeliveryLog instances
        """
        return self.db.query(DeliveryLog).filter(
            DeliveryLog.delivered_at >= start_date,
            DeliveryLog.delivered_at <= end_date
        ).order_by(DeliveryLog.delivered_at.desc()).offset(skip).limit(limit).all()
    
    def get_user_problem_delivery(self, user_id: UUID, problem_id: UUID) -> Optional[DeliveryLog]:
        """
        Get the delivery log for a specific user and problem combination.
        
        Args:
            user_id: User ID
            problem_id: Problem ID
            
        Returns:
            DeliveryLog instance or None if not found
        """
        return self.db.query(DeliveryLog).filter(
            DeliveryLog.user_id == user_id,
            DeliveryLog.problem_id == problem_id
        ).first()
    
    def count_by_status(self) -> Dict[str, int]:
        """
        Count delivery logs by status.
        
        Returns:
            Dictionary with status values as keys and counts as values
        """
        # Initialize with default counts for all possible statuses
        from app.db.models.delivery_log import DeliveryStatus
        
        # Initialize result with all possible statuses set to 0
        result = {status.value: 0 for status in DeliveryStatus}
        
        # Get actual counts from database
        query = self.db.query(
            DeliveryLog.status,
            func.count(DeliveryLog.id)
        ).group_by(DeliveryLog.status).all()
        
        # Update result with actual counts - handle both string and enum keys
        for status, count in query:
            # When status is an enum object, use its string value
            if hasattr(status, 'value'):
                result[status.value] = count
            else:
                # When status is already a string
                result[status] = count
            
        return result
