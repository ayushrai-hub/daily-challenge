"""
Admin-specific user repository functions.
"""
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_, func
# Import context variables to access request context
from app.core.middleware import request_id_ctx_var, user_id_ctx_var, user_email_ctx_var, user_is_admin_ctx_var

from app.db.models.user import User, SubscriptionStatus
from app.repositories.user import UserRepository
from app.schemas.admin_user import AdminUserUpdate


class AdminUserRepository(UserRepository):
    """Repository for admin-level user operations."""
    
    def __init__(self, db: Session):
        super().__init__(db=db)
    
    def get_all_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> Tuple[List[User], int]:
        """
        Get all users with filtering and search capabilities.
        
        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            filters: Dictionary of field-value pairs to filter users
            search: Search term to filter users by email or full_name
            
        Returns:
            Tuple of (list of User instances, total count)
        """
        # Start with base query
        query = self.db.query(User)
        count_query = self.db.query(func.count(User.id))
        
        # Apply search if provided
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%") if User.full_name else False
            )
            query = query.filter(search_filter)
            count_query = count_query.filter(search_filter)
        
        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if field == "email" and isinstance(value, str):
                        query = query.filter(User.email.ilike(f"%{value}%"))
                        count_query = count_query.filter(User.email.ilike(f"%{value}%"))
                    elif field == "full_name" and isinstance(value, str):
                        query = query.filter(User.full_name.ilike(f"%{value}%"))
                        count_query = count_query.filter(User.full_name.ilike(f"%{value}%"))
                    else:
                        query = query.filter(getattr(User, field) == value)
                        count_query = count_query.filter(getattr(User, field) == value)
        
        # Get total count
        total_count = count_query.scalar()
        
        # Apply pagination and return results
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users, total_count
    
    def admin_update_user(self, user_id: UUID, update_data: AdminUserUpdate) -> Optional[User]:
        """
        Update a user with admin privileges (allows updating fields regular users can't).
        
        Args:
            user_id: ID of the user to update
            obj_in: AdminUserUpdate object with fields to update
            
        Returns:
            Updated User instance or None if not found
        """
        # Get user by ID
        user = self.get(user_id)
        if not user:
            return None
        
        # Update user with provided data
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Log the update data for debugging
        logger = logging.getLogger("app.repositories.admin_user")
        logger.info(
            f"Updating user {user_id}",
            extra={
                # Get request_id from context variable
                "request_id": request_id_ctx_var.get(""),
                "user_id": str(user_id),
                "user_email": user_email_ctx_var.get(""),
                "is_admin": user_is_admin_ctx_var.get(False),
                "update_fields": list(update_dict.keys()),
                "full_name_updated": "full_name" in update_dict,
                "full_name_value": update_dict.get("full_name", None)
            }
        )
        
        return self.update(db_obj=user, obj_in=update_dict)
    
    def toggle_admin_status(self, user_id: UUID, make_admin: bool) -> Optional[User]:
        """
        Set or unset admin status for a user.
        
        Args:
            user_id: ID of the user to update
            make_admin: Boolean flag for admin status
            
        Returns:
            Updated User instance or None if not found
        """
        user = self.get(user_id)
        if not user:
            return None
        
        user.is_admin = make_admin
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def toggle_user_active_status(self, user_id: UUID, make_active: bool) -> Optional[User]:
        """
        Set or unset active status for a user.
        
        Args:
            user_id: ID of the user to update
            make_active: Boolean flag for active status
            
        Returns:
            Updated User instance or None if not found
        """
        user = self.get(user_id)
        if not user:
            return None
        
        user.is_active = make_active
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
