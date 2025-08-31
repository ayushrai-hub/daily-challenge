"""
Problem Selection Service for Daily Challenge Emails

This module handles the core logic for selecting relevant problems for users based on
their subscribed tags, incorporating:
- Tag hierarchy awareness (parent-child tag relationships)
- Problem rotation
- Avoidance of recently sent problems
- Fallback logic when exact matches aren't available
"""
from typing import List, Optional, Set, Dict, Any, Tuple, Union
from uuid import UUID
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, not_, desc, asc

from app.db.models.user import User
from app.db.models.tag import Tag
from app.db.models.problem import Problem, ProblemStatus
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.delivery_log import DeliveryLog
from app.core.logging import get_logger

logger = get_logger()

class ProblemSelector:
    """
    Service responsible for selecting appropriate problems for users based on their tag preferences,
    incorporating tag hierarchy relationships and problem rotation strategies.
    """
    
    MINIMUM_RESEND_DAYS = 30  # Minimum days before a problem can be resent to the same user
    
    @classmethod
    async def select_problem_for_user(
        cls, 
        db: Session, 
        user_id: UUID
    ) -> Optional[Problem]:
        """
        Select an appropriate problem for a user, taking into account:
        1. User's tag preferences (including child tags via tag hierarchy)
        2. Previously sent problems
        3. Problem approval status
        
        Args:
            db: Database session
            user_id: ID of the user to select a problem for
            
        Returns:
            Problem or None if no suitable problem found
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User not found for ID: {user_id}")
            return None
            
        if not user.is_active or not user.is_email_verified:
            logger.info(f"User {user_id} is not active or not verified, skipping problem selection")
            return None
            
        # Get problems based on tag preferences with tag hierarchy awareness
        problem = await cls._select_problem_with_tag_hierarchy(db, user)
        
        # If no problem found with tag matching, try fallback strategies
        if not problem:
            logger.info(f"No tagged problem found for user {user_id}, trying fallback")
            problem = await cls._select_fallback_problem(db, user)
            
        if problem:
            logger.info(f"Selected problem {problem.id} ('{problem.title}') for user {user_id}")
        else:
            logger.warning(f"No suitable problem found for user {user_id}")
            
        return problem
    
    @classmethod
    async def _select_problem_with_tag_hierarchy(
        cls, 
        db: Session, 
        user: User
    ) -> Optional[Problem]:
        """
        Select a problem that matches the user's tag preferences, considering
        tag hierarchy (i.e., a user subscribed to a parent tag should also receive
        problems tagged with child tags).
        
        Args:
            db: Database session
            user: User to select problem for
            
        Returns:
            Problem or None if no suitable problem found
        """
        # Get the user's subscribed tag IDs
        user_tag_ids = [tag.id for tag in user.tags]
        
        if not user_tag_ids:
            logger.info(f"User {user.id} has no subscribed tags")
            return None
        
        # Get all child tags of the user's subscribed tags using tag hierarchy
        expanded_tag_ids = set(user_tag_ids)
        
        # Add child tags (recursive) from the user's subscribed tags
        for tag_id in user_tag_ids:
            child_tags = cls._get_all_child_tags(db, tag_id)
            expanded_tag_ids.update(child_tag.id for child_tag in child_tags)
        
        logger.debug(f"Expanded tag IDs for user {user.id}: {expanded_tag_ids}")
        
        # Query for problems matching the expanded tag set
        # Avoid problems sent to this user within the last MINIMUM_RESEND_DAYS
        min_resend_date = datetime.utcnow() - timedelta(days=cls.MINIMUM_RESEND_DAYS)
        
        # Check if the user has been sent a problem before
        resend_filter = True  # Always true in case there's no delivery log yet
        if user.last_problem_sent_id and user.last_problem_sent_at:
            resend_filter = or_(
                # Either the problem was never sent to this user
                Problem.id.notin_(
                    db.query(Problem.id)
                    .join(Problem.delivery_logs)
                    .filter(
                        and_(
                            Problem.delivery_logs.any(user_id=user.id),
                            # Only consider problems sent within the minimum resend period
                            Problem.delivery_logs.any(DeliveryLog.delivered_at >= min_resend_date)
                        )
                    )
                ),
                # Or it was sent long enough ago to be eligible for resending
                and_(
                    Problem.delivery_logs.any(user_id=user.id),
                    not_(Problem.delivery_logs.any(DeliveryLog.delivered_at >= min_resend_date))
                )
            )
        
        # Query for problems
        # 1. Problem has one of the expanded tags
        # 2. Problem is approved
        # 3. Problem hasn't been sent to this user recently
        query = (
            db.query(Problem)
            .filter(
                Problem.tags.any(Tag.id.in_(expanded_tag_ids)),
                Problem.status == ProblemStatus.approved,
                resend_filter
            )
            # Order by newest problems first to prioritize fresh content
            .order_by(desc(Problem.created_at))
        )
        
        problem = query.first()
        
        # Additional logging for query debugging
        if not problem:
            tag_names = db.query(Tag.name).filter(Tag.id.in_(expanded_tag_ids)).all()
            logger.info(
                f"No matching problem found for user {user.id} with "
                f"tags: {[t[0] for t in tag_names]}"
            )
            
        return problem
    
    @classmethod
    def _get_all_child_tags(cls, db: Session, tag_id: UUID) -> List[Tag]:
        """
        Recursively get all child tags for a given tag ID using the tag hierarchy.
        
        Args:
            db: Database session
            tag_id: Parent tag ID
            
        Returns:
            List of all child Tag objects (recursive)
        """
        # Get direct children
        direct_children = (
            db.query(Tag)
            .join(
                TagHierarchy,
                and_(
                    TagHierarchy.child_tag_id == Tag.id,
                    TagHierarchy.parent_tag_id == tag_id
                )
            )
            .all()
        )
        
        # Initialize result with direct children
        all_children = direct_children.copy()
        
        # Recursively get children of children
        for child in direct_children:
            all_children.extend(cls._get_all_child_tags(db, child.id))
            
        return all_children
    
    @classmethod
    async def _select_fallback_problem(
        cls, 
        db: Session, 
        user: User
    ) -> Optional[Problem]:
        """
        Select a fallback problem when no exact tag match is found.
        Fallback logic:
        1. Try any problem not yet sent to the user
        2. If all problems have been sent, select oldest sent problem (respecting minimum resend days)
        
        Args:
            db: Database session
            user: User to select problem for
            
        Returns:
            Problem or None if no suitable problem found
        """
        # Try to find any approved problem not sent to this user
        unsent_problem = (
            db.query(Problem)
            .filter(
                Problem.status == ProblemStatus.approved,
                not_(Problem.delivery_logs.any(user_id=user.id))
            )
            .order_by(desc(Problem.created_at))
            .first()
        )
        
        if unsent_problem:
            logger.info(f"Selected fallback (unsent) problem for user {user.id}")
            return unsent_problem
            
        # If all problems have been sent to the user, select the oldest sent problem
        # (respecting minimum resend days)
        min_resend_date = datetime.utcnow() - timedelta(days=cls.MINIMUM_RESEND_DAYS)
        
        oldest_sent_problem = (
            db.query(Problem)
            .join(Problem.delivery_logs)
            .filter(
                Problem.status == ProblemStatus.approved,
                Problem.delivery_logs.any(user_id=user.id),
                # Ensure it was sent long enough ago
                not_(Problem.delivery_logs.any(
                    and_(
                        Problem.delivery_logs.user_id == user.id,
                        DeliveryLog.delivered_at >= min_resend_date
                    )
                ))
            )
            .order_by(asc(DeliveryLog.delivered_at))
            .first()
        )
        
        if oldest_sent_problem:
            logger.info(f"Selected fallback (resend) problem for user {user.id}")
            
        return oldest_sent_problem
