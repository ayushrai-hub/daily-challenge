from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import select, func
from datetime import datetime

from app.db.models.problem import Problem, VettingTier, ProblemStatus
from app.schemas.problem import ProblemCreate, ProblemUpdate
from app.repositories.base import BaseRepository


class ProblemRepository(BaseRepository[Problem, ProblemCreate, ProblemUpdate]):
    """Repository for Problem model providing CRUD operations and problem-specific queries."""
    
    def __init__(self, db: Session):
        super().__init__(model=Problem, db=db)
    
    def get_by_title(self, title: str) -> Optional[Problem]:
        """
        Get a problem by title.
        
        Args:
            title: Problem title to search for
            
        Returns:
            Problem instance or None if not found
        """
        return self.db.query(Problem).filter(Problem.title == title).first()
    
    def get_by_vetting_tier(self, tier: VettingTier, skip: int = 0, limit: int = 100) -> List[Problem]:
        """
        Get problems by vetting tier.
        
        Args:
            tier: Vetting tier to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of Problem instances
        """
        return self.db.query(Problem).filter(
            Problem.vetting_tier == tier
        ).offset(skip).limit(limit).all()
    
    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[Problem]:
        """
        Get problems by status.
        
        Args:
            status: Status to filter by (e.g., 'pending', 'approved')
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of Problem instances
        """
        return self.db.query(Problem).filter(
            Problem.status == status
        ).offset(skip).limit(limit).all()
    
    def get_by_content_source(self, content_source_id: UUID, skip: int = 0, limit: int = 100) -> List[Problem]:
        """
        Get problems by content source ID.
        
        Args:
            content_source_id: Content source ID to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of Problem instances
        """
        return self.db.query(Problem).filter(
            Problem.content_source_id == content_source_id
        ).offset(skip).limit(limit).all()
    
    def get_problems_with_tags(self, tag_ids: List[UUID], skip: int = 0, limit: int = 100) -> List[Problem]:
        """
        Get problems that have specific tags.
        
        Args:
            tag_ids: List of tag IDs to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            
        Returns:
            List of Problem instances
        """
        from app.db.models.tag import Tag
        return self.db.query(Problem).filter(
            Problem.tags.any(Tag.id.in_(tag_ids))
        ).offset(skip).limit(limit).all()
    
    def update_vetting_tier(self, problem_id: UUID, new_tier: VettingTier) -> Optional[Problem]:
        """
        Update a problem's vetting tier.
        
        Args:
            problem_id: ID of the problem to update
            new_tier: New vetting tier
            
        Returns:
            Updated Problem instance or None if not found
        """
        problem = self.get(problem_id)
        if not problem:
            return None
        
        problem.vetting_tier = new_tier
        self.db.add(problem)
        self.db.commit()
        self.db.refresh(problem)
        return problem
        
    def update_status(self, problem_id: UUID, new_status: ProblemStatus, reviewer_id: Optional[UUID] = None) -> Optional[Problem]:
        """
        Update a problem's status.
        
        Args:
            problem_id: ID of the problem to update
            new_status: New status (draft, approved, archived, pending)
            reviewer_id: Optional ID of the admin who approved/updated the problem
            
        Returns:
            Updated Problem instance or None if not found
        """
        problem = self.get(problem_id)
        if not problem:
            return None
        
        problem.status = new_status
        
        # Set approved_at timestamp when problem is approved
        if new_status == ProblemStatus.approved and problem.approved_at is None:
            problem.approved_at = datetime.now()
            
            # If we have problem_metadata as a dict, we can store reviewer info
            if problem.problem_metadata is None:
                problem.problem_metadata = {}
                
            if reviewer_id:
                problem.problem_metadata["approved_by"] = str(reviewer_id)
                problem.problem_metadata["approval_history"] = problem.problem_metadata.get("approval_history", []) + [
                    {"status": "approved", "timestamp": datetime.now().isoformat(), "reviewer_id": str(reviewer_id)}
                ]
            
        # Clear approved_at if a problem is being moved back to draft or pending
        elif new_status in [ProblemStatus.draft, ProblemStatus.pending]:
            # Don't clear the timestamp, but add to approval history that it was unapproved
            if reviewer_id and problem.problem_metadata is not None:
                problem.problem_metadata["approval_history"] = problem.problem_metadata.get("approval_history", []) + [
                    {"status": "unapproved", "timestamp": datetime.now().isoformat(), "reviewer_id": str(reviewer_id)}
                ]
        
        self.db.add(problem)
        self.db.commit()
        self.db.refresh(problem)
        return problem
