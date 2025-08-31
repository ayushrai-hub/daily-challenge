from typing import List, Optional, Dict, Any, Union, Type, Set, Tuple

from sqlalchemy.orm import Session, joinedload, aliased
from uuid import UUID
from sqlalchemy import select, func, and_,cast, or_, text, String

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import uuid
import threading
from app.db.models.tag import Tag, TagType
from app.db.models.tag_hierarchy import TagHierarchy
from app.db.models.tag_normalization import TagNormalization, TagReviewStatus, TagSource
from app.schemas.tag import TagCreate, TagUpdate
from app.schemas.tag_hierarchy import TagHierarchyCreate
from app.schemas.tag_normalization import TagNormalizationCreate, TagNormalizationUpdate
from app.repositories.base import BaseRepository
from app.core.logging import get_logger

logger = get_logger()

# Global tag registry to prevent race conditions and duplicate tag creation across the application
class TagRegistry:
    """A global registry for ensuring uniqueness of tags across the application."""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TagRegistry, cls).__new__(cls)
                cls._instance._registry = {}
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
        with self._lock:
            self._initialized = True
            self._registry = {}  # Maps lowercase str(tag.name).split() to Tag instances
    
    def register(self, tag: Tag) -> None:
        """Register an existing tag in the registry."""
        if not tag or not tag.name:
            return
        
        with self._lock:
            # Use case-insensitive key (lowercase)
            key = str(tag.name).lower()
            self._registry[key] = tag
            logger.debug(f"Registered tag in registry: {tag.name} (ID: {tag.id})")
    
    def get(self, name: str) -> Optional[Tag]:
        """Get a tag from the registry by name (case insensitive)."""
        if not name or not name.strip():
            return None
        
        with self._lock:
            key = name.strip().lower()
            return self._registry.get(key)
    
    def clear(self) -> None:
        """Clear the registry (used for testing)."""
        with self._lock:
            self._registry.clear()

# Global singleton instance of the tag registry
tag_registry = TagRegistry()


class TagRepository(BaseRepository[Tag, TagCreate, TagUpdate]):
    """Repository for Tag model providing CRUD operations and tag-specific queries."""
    
    def __init__(self, db: Session):
        super().__init__(model=Tag, db=db)
        
    def get_or_create_tag_upsert(self, name: str, **kwargs) -> Tag:
        """
        Get or create a tag using a database-level upsert operation to handle race conditions.
        This is the most robust way to handle tag creation in a distributed environment.
        
        Args:
            name: The tag name to look up or create
            **kwargs: Additional tag attributes (tag_type, description, etc.)
            
        Returns:
            The existing or newly created Tag instance
        """
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")
        
        clean_name = name.strip()
        
        # Generate a new UUID for potential insertion
        tag_id = uuid.uuid4()
        
        # Prepare optional fields with defaults
        description = kwargs.get('description')
        tag_type = kwargs.get('tag_type')
        is_featured = kwargs.get('is_featured', False)
        is_private = kwargs.get('is_private', False)
        
        try:
            # Use an upsert operation via raw SQL to atomically insert or get the existing tag
            # PostgreSQL's ON CONFLICT ensures this is handled at the database level
            sql_query = text("""
                INSERT INTO tags (id, name, description, tag_type, is_featured, is_private)
                VALUES (:id, :name, :description, :tag_type, :is_featured, :is_private)
                ON CONFLICT (lower(name)) DO
                UPDATE
                SET name = tags.name  -- Keep the existing capitalization
                RETURNING id, name, description, tag_type, is_featured, is_private
            """)
            
            result = self.db.execute(sql_query, {
                    "id": tag_id, 
                    "name": clean_name,
                    "description": description,
                    "tag_type": tag_type,
                    "is_featured": is_featured,
                    "is_private": is_private
                })
            
            # Get the result row (either inserted or existing)
            row = result.fetchone()
            
            # Fetch the tag object from the database using the returned ID
            tag = self.db.query(Tag).filter(Tag.id == row.id).first()
            
            # Log the operation
            if str(row.id) == str(tag_id):
                logger.info(f"Created new tag with upsert: {tag.name} (ID: {tag.id})")
            else:
                logger.info(f"Found existing tag with upsert: {tag.name} (ID: {tag.id})")
            
            # Ensure the tag is added to the global registry if that's still in use
            if 'tag_registry' in globals():
                tag_registry.register(tag)
                
            # Return the tag
            return tag
            
        except Exception as e:
            logger.error(f"Error in upsert operation for tag '{clean_name}': {str(e)}")
            self.db.rollback()
            
            # As a fallback, try a direct case-insensitive lookup
            existing_tag = self.get_by_name_case_insensitive_safe(clean_name)
            if existing_tag:
                return existing_tag
                
            # If all else fails, raise the exception
            raise
            
    def get_or_create_case_insensitive(self, name: str, **kwargs) -> Tag:
        """
        Wrapper for get_or_create_tag_upsert with backward compatibility.
        Use the more robust upsert method internally.
        
        Args:
            name: The tag name to look up or create
            **kwargs: Additional tag attributes
            
        Returns:
            The existing or newly created Tag instance
        """
        try:
            # First try getting tag by case-insensitive search to avoid unnecessary creation
            existing_tag = self.get_by_name_case_insensitive_safe(str(name))
            if existing_tag:
                return existing_tag
                
            # If not found, call the upsert method with any provided keyword arguments
            return self.get_or_create_tag_upsert(name, **kwargs)
        except Exception as e:
            logger.error(f"Error in get_or_create_case_insensitive for '{name}': {str(e)}")
            # Fall back to the direct upsert as a last resort
            return self.get_or_create_tag_upsert(name, **kwargs)
        
    def get_or_create_case_insensitive_name_only(self, name: str, **kwargs) -> str:
        """
        Session-safe version that returns only the tag name, not the Tag object.
        This avoids session binding issues when used across session boundaries.
        
        Args:
            name: The tag name to look up or create
            **kwargs: Additional tag attributes
            
        Returns:
            The canonical tag name (string) - NEVER the Tag object
        """
        # Get the tag using upsert
        tag = self.get_or_create_tag_upsert(name, **kwargs)
        # Return just the name
        return str(tag.name) if tag else name
            
    async def get_or_create_tag_upsert_async(self, session: AsyncSession, name: str, **kwargs) -> Tag:
        """
        Async version of get_or_create_tag_upsert.
        Uses a database-level upsert operation to handle race conditions.
        
        Args:
            session: Async database session
            name: The tag name to look up or create
            **kwargs: Additional tag attributes (tag_type, description, etc.)
            
        Returns:
            The existing or newly created Tag instance
        """
        if not name or not name.strip():
            raise ValueError("Tag name cannot be empty")
        
        clean_name = name.strip()
        
        # Generate a new UUID for potential insertion
        tag_id = uuid.uuid4()
        
        # Prepare optional fields with defaults
        description = kwargs.get('description')
        tag_type = kwargs.get('tag_type')
        is_featured = kwargs.get('is_featured', False)
        is_private = kwargs.get('is_private', False)
        
        try:
            # Use an upsert operation via raw SQL to atomically insert or get the existing tag
            # We need to use the raw SQL execute method for the async session
            stmt = text("""
                INSERT INTO tags (id, name, description, tag_type, is_featured, is_private)
                VALUES (:id, :name, :description, :tag_type, :is_featured, :is_private)
                ON CONFLICT (lower(name)) DO UPDATE 
                SET name = tags.name  -- Keep the existing capitalization
                RETURNING id
            """)
            
            params = {
                "id": tag_id, 
                "name": clean_name,
                "description": description,
                "tag_type": tag_type,
                "is_featured": is_featured,
                "is_private": is_private
            }
            
            # Execute the statement
            result = await session.execute(stmt, params)
            
            # Get the result row with the tag ID (either new or existing)
            row = result.fetchone()
            if row is None:
                raise ValueError("No result returned from upsert operation")
                
            returned_id = row[0]  # First column is the ID
            
            # Fetch the tag object from the database using the returned ID
            tag_query = select(Tag).where(Tag.id == returned_id)
            tag_result = await session.execute(tag_query)
            tag = tag_result.scalars().first()
            
            # Log the operation
            if str(returned_id) == str(tag_id):
                logger.info(f"Created new tag with async upsert: {tag.name} (ID: {tag.id})")
            else:
                logger.info(f"Found existing tag with async upsert: {tag.name} (ID: {tag.id})")
            
            # Register the tag in the global registry
            tag_registry.register(tag)
            
            # Ensure the tag is properly bound to the session
            # Using merge to attach the object to the current session if it isn't already
            # This is critical for async contexts where session binding can be lost
            try:
                tag = await session.merge(tag)
                logger.debug(f"Merged tag {tag.name} into current session to ensure proper binding")
            except Exception as merge_error:
                logger.warning(f"Error merging tag into session (non-critical): {str(merge_error)}")
            
            return tag
            
        except Exception as e:
            logger.error(f"Error in async upsert operation for tag '{clean_name}': {str(e)}")
            await session.rollback()
            
            # As a fallback, try a direct case-insensitive lookup
            query = select(Tag).where(func.lower(Tag.name) == func.lower(clean_name))
            result = await session.execute(query)
            existing_tag = result.scalars().first()
            if existing_tag:
                return existing_tag
                
            # If all else fails, raise the exception
            raise
    
    async def get_or_create_case_insensitive_async(self, session: AsyncSession, name: str, **kwargs) -> Tag:
        """
        Async wrapper for get_or_create_tag_upsert_async with backward compatibility.
        
        Args:
            session: Async database session
            name: The tag name to look up or create
            **kwargs: Additional tag attributes
            
        Returns:
            The existing or newly created Tag instance
        """
        # Call the upsert method with any provided keyword arguments
        return await self.get_or_create_tag_upsert_async(session, name, **kwargs)
        
    def create(self, obj_in: TagCreate) -> Tag:
        """
        Create a new tag and set up parent-child relationships.
        This method overrides the base repository's create method to handle
        the multi-parent tag hierarchy.
        
        Args:
            obj_in: Tag creation data
            
        Returns:
            Created Tag instance with proper relationships
        """
        try:
            # Create dictionary of input data
            input_data = obj_in.model_dump()
            logger.info(f"Creating Tag with data: {obj_in}")
            logger.info(f"Encoded data: {input_data}")
            
            # Handle possible UUID string fields
            uuid_fields = ['id', 'parent_tag_id']  # parent_tag_id for backward compatibility
            for field in uuid_fields:
                if field in input_data and isinstance(input_data[field], str):
                    try:
                        input_data[field] = UUID(input_data[field])
                        logger.info(f"Converted {field} from string to UUID: {input_data[field]}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Error converting {field} to UUID: {e}")
            
            # Extract parent_ids field to handle separately
            parent_ids = input_data.pop('parent_ids', [])
            
            # Handle parent_tag_id for backward compatibility
            parent_tag_id = input_data.pop('parent_tag_id', None)
            if parent_tag_id is not None and parent_tag_id not in parent_ids:
                parent_ids.append(parent_tag_id)  # type: ignore
            
            # Create a clean data dictionary with the appropriate model fields
            model_fields = {column.key for column in self.model.__table__.columns if hasattr(column, 'key')}  # type: ignore
            cleaned_data = {k: v for k, v in input_data.items() if k in model_fields}
            
            logger.info(f"Cleaned data for model creation: {cleaned_data}")
            
            # Create tag without parent relationships first
            db_obj = self.model(**cleaned_data)  # type: ignore
            self.db.add(db_obj)
            self.db.flush()  # Flush to get the ID but don't commit yet
            
            # Now set up the parent-child relationships using the junction table
            for parent_id in parent_ids:
                # Skip invalid UUIDs
                if not isinstance(parent_id, UUID) and isinstance(parent_id, str):
                    try:
                        parent_id = UUID(parent_id)
                    except (ValueError, AttributeError):
                        logger.warning(f"Invalid parent ID: {parent_id}, skipping")
                        continue
                
                # Skip adding if it would create a cycle
                if self.would_create_cycle(parent_id, db_obj.id):
                    logger.warning(f"Skipping parent ID {parent_id} that would create a cycle")
                    continue
                
                # Add the parent-child relationship
                hierarchy = TagHierarchy(
                    parent_tag_id=parent_id,
                    child_tag_id=db_obj.id,
                    relationship_type="parent_child"
                )
                self.db.add(hierarchy)
                logger.info(f"Added tag hierarchy relationship: Parent {parent_id} -> Child {db_obj.id}")
            
            # Commit all changes
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating tag: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def get_by_name(self, name: str) -> Optional[Tag]:
        """
        Get a tag by name.
        
        Args:
            name: Tag name to search for
            
        Returns:
            Tag instance or None if not found
        """
        return self.db.query(Tag).filter(Tag.name == name).first()
    
    def get_by_field(self, field: str, value: Any) -> Optional[Tag]:
        """
        Get a tag by a specific field value.
        
        Args:
            field: Field name to search on
            value: Value to search for
            
        Returns:
            Tag instance or None if not found
        """
        if not hasattr(self.model, field):
            return None
        
        return self.db.query(self.model).filter(getattr(self.model, field) == value).first()
        
    def get_by_name_case_insensitive(self, name: str) -> Optional[Tag]:
        """
        Get a tag by name using case-insensitive matching.
        Prioritizes properly cased tags when multiple matches exist with different casing.
        
        Args:
            name: Tag name to search for (case insensitive)
            
        Returns:
            Tag instance or None if not found
        """
        if not name:
            return None
            
        try:
            # Direct database query to avoid recursion
            # First try an exact match (case-sensitive)
            tag = self.db.query(Tag).filter(Tag.name == name).first()
            if tag:
                return tag
                
            # If no exact match, try case-insensitive match
            tag = self.db.query(Tag).filter(func.lower(Tag.name) == func.lower(name)).first()
            return tag
        except Exception as e:
            logger.error(f"Error in direct get_by_name_case_insensitive query: {str(e)}")
            return None

    def name_exists_case_insensitive(self, name: str) -> bool:
        """
        Check if a tag with the given name exists in the database (case insensitive).
        This method avoids session binding issues by not returning the actual tag object.
        
        Args:
            name: Tag name to check for (case insensitive)
            
        Returns:
            True if a tag with this name exists, False otherwise
        """
        # Clean the input name
        clean_name = name.strip() if name else ""
        if not clean_name:
            return False
            
        # Check the registry first for improved performance
        if tag_registry.get(clean_name):
            return True
            
        try:
            # Just check existence without returning the object
            count = self.db.query(Tag).filter(
                func.lower(Tag.name) == func.lower(clean_name)
            ).count()
            
            return count > 0
            
        except Exception as e:
            logger.error(f"Error checking tag existence: {str(e)}")
            return False
    
    def get_canonical_name(self, name: str) -> Optional[str]:
        """
        Get the canonical name (with proper casing) for a tag name.
        This helps ensure consistent tag names across the system.
        
        Args:
            name: Tag name to get canonical version for (case insensitive)
            
        Returns:
            Canonical tag name or None if not found
        """
        # Clean the input name
        clean_name = name.strip() if name else ""
        if not clean_name:
            return None
            
        # Check the registry first
        tag = tag_registry.get(clean_name)
        if tag:
            return str(tag.name)
            
        try:
            # Query just the name to avoid session binding issues
            from sqlalchemy import func
            
            result = self.db.query(Tag.name).filter(
                func.lower(Tag.name) == func.lower(clean_name)
            ).first()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error getting canonical tag name: {str(e)}")
            return None
            
    def get_by_name_case_insensitive_safe(self, name: str) -> Optional[Tag]:
        """
        Safe version of get_by_name_case_insensitive that works with the enhanced Tag model.
        This version is designed to work with the properly configured self-referential relationships
        and also populates the tag registry for future lookups.
        
        Args:
            name: Tag name to search for (case insensitive)
            
        Returns:
            Tag instance or None if not found
        """
        try:
            if not name:
                return None
                
            # Look up in the tag registry first (if available)
            registry_tag = None
            if 'tag_registry' in globals():
                registry_tag = tag_registry.get(name)
            if registry_tag:
                return registry_tag
                
            # Directly query the databasex to avoid recursion issues
            # First try exact match
            tag = self.db.query(Tag).filter(Tag.name == name).first()
            if tag:
                return tag
                
            # Then try case-insensitive match
            tag = self.db.query(Tag).filter(func.lower(Tag.name) == func.lower(name)).first()
            if tag and 'tag_registry' in globals():
                # Add to registry for future lookups
                tag_registry.register(tag)
                
            return tag
                
        except Exception as e:
            logger.error(f"Error in get_by_name_case_insensitive_safe: {str(e)}")
            return None
            
    def get_by_normalized_name(self, normalized_name: str) -> Optional[Tag]:
        """
        This performs a more aggressive match by scanning all tags and comparing normalized forms.
        
        Args:
            normalized_name: Normalized tag name to search for (lowercase, no spaces)
            
        Returns:
            Tag instance or None if not found, prioritizing proper casing if multiple matches exist
        """
        # Defensive check to prevent NoneType errors
        if normalized_name is None or not normalized_name:
            logger.warning("get_by_normalized_name called with None or empty name")
            return None
        
        # Ensure normalized_name is actually normalized and is a string
        try:
            normalized_name = ''.join(str(normalized_name).lower().split())
        except Exception as e:
            logger.error(f"Error normalizing tag name: {str(e)}")
            return None
        
        # Scan all tags (we're doing a full table scan, but the tag table should be relatively small)
        try:
            all_tags = self.db.query(self.model).all()
        except Exception as e:
            logger.error(f"Error querying tags: {str(e)}")
            return None
        
        # We'll keep track of all matches but prioritize proper casing
        all_matches = []
        
        for tag in all_tags:
            # Normalize the existing tag name
            normalized_tag_name = ''.join(str(tag.name).lower().split())
            
            # Compare normalized forms
            if normalized_tag_name == normalized_name:
                logger.info(f"Found match for normalized tag '{normalized_name}': '{tag.name}'")
                all_matches.append(tag)
        
        if not all_matches:
            return None
            
        # If multiple matches, prioritize the one with proper casing (not all lowercase or all uppercase)
        if len(all_matches) > 1:
            for tag in all_matches:
                # Proper casing typically has mixed case (not all lower, not all upper)
                if str(tag.name) != str(tag.name).lower() and str(tag.name) != str(tag.name).upper():
                    logger.info(f"Selected properly cased tag '{tag.name}' from multiple matches")
                    return tag
        
        # Otherwise, just return the first match
        return all_matches[0]
    
    def get_tags_for_user(self, user_id: UUID) -> List[Tag]:
        """
        Get all tags associated with a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of Tag instances
        """
        return self.db.query(Tag).filter(
            Tag.users.any(id=user_id)
        ).all()
    
    def get_tags_for_problem(self, problem_id: UUID) -> List[Tag]:
        """
        Get all tags associated with a specific problem.
        
        Args:
            problem_id: ID of the problem
            
        Returns:
            List of Tag instances
        """
        return self.db.query(Tag).filter(
            Tag.problems.any(id=problem_id)
        ).all()
    
    def get_child_tags(self, parent_tag_id: UUID) -> List[Tag]:
        """
        Get all child tags for a given parent tag using the tag_hierarchy junction table.
        
        Args:
            parent_tag_id: ID of the parent tag
            
        Returns:
            List of child Tag instances
        """
        return self.db.query(Tag).join(
            TagHierarchy, 
            and_(
                TagHierarchy.child_tag_id == Tag.id,
                TagHierarchy.parent_tag_id == parent_tag_id
            )
        ).all()
        
    def get_parent_tags(self, child_tag_id: UUID) -> List[Tag]:
        """
        Get all parent tags for a given child tag using the tag_hierarchy junction table.
        
        Args:
            child_tag_id: ID of the child tag
            
        Returns:
            List of parent Tag instances
        """
        return self.db.query(Tag).join(
            TagHierarchy, 
            and_(
                TagHierarchy.parent_tag_id == Tag.id,
                TagHierarchy.child_tag_id == child_tag_id
            )
        ).all()
    
    def get_all_ancestors(self, tag_id: UUID) -> List[Tag]:
        """
        Get all ancestors (direct and indirect parents) of a tag.
        
        Args:
            tag_id: ID of the tag to get ancestors for
            
        Returns:
            List of Tag instances that are ancestors of the given tag
        """
        ancestors = set()
        visited = set()
        
        def collect_ancestors(current_id):
            if current_id in visited:
                return
            
            visited.add(current_id)
            
            # Get direct parents
            parents = self.get_parent_tags(current_id)
            
            for parent in parents:
                ancestors.add(parent)
                # Recursively find all ancestors
                collect_ancestors(parent.id)
        
        # Start collecting ancestors
        collect_ancestors(tag_id)
        
        return list(ancestors)
    
    def get(self, id: UUID) -> Optional[Tag]:
        """
        Get a single tag by ID.
        
        Args:
            id: ID of the tag to retrieve
            
        Returns:
            Tag instance or None if not found
        """
        return super().get(id)
    
    def get_multi(self, *, skip: int = 0, limit: int = 100, **filters) -> List[Tag]:
        """
        Get multiple tags with optional pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Additional filters to apply
            
        Returns:
            List of Tag instances
        """
        return super().get_multi(skip=skip, limit=limit, **filters)
    
    def get_with_children(self, id: UUID) -> Optional[Tag]:
        """
        Get a tag by ID with its children preloaded using the tag_hierarchy junction table.
        
        Args:
            id: Tag ID
            
        Returns:
            Tag instance with children relationship preloaded or None if not found
        """
        # Get the tag first
        tag = self.db.query(self.model).filter(self.model.id == id).first()
        if not tag:
            return None
            
        # Then fetch all child tags and attach them as a property
        child_tags = self.get_child_tags(tag.id)
        setattr(tag, "children", child_tags)
            
        return tag
        
    def add_parent_child_relationship(self, parent_id: UUID, child_id: UUID, relationship_type: str = "parent_child") -> bool:
        """
        Add a parent-child relationship between two tags if it doesn't create a cycle.
        
        Args:
            parent_id: ID of the parent tag
            child_id: ID of the child tag
            relationship_type: Type of relationship (default is 'parent_child')
            
        Returns:
            True if relationship was added successfully, False if it would create a cycle
            or if either tag doesn't exist
        """
        # Check that both tags exist
        parent = self.get(parent_id)
        child = self.get(child_id)
        if not parent or not child:
            logger.error(f"Cannot create relationship: Parent or child tag doesn't exist. Parent ID: {parent_id}, Child ID: {child_id}")
            return False
            
        # Don't allow self-referential relationships
        if parent_id == child_id:
            logger.error(f"Cannot create relationship: Self-referential relationships are not allowed. Tag ID: {parent_id}")
            return False
            
        # Check if relationship would create a cycle
        if self.would_create_cycle(parent_id, child_id):
            error_msg = f"Cannot create relationship: It would create a cycle. Parent: {parent.name}, Child: {child.name}"
            logger.error(error_msg)
            raise ValueError(f"Adding this relationship would create a cycle in the tag hierarchy.")
            
        # Create the relationship
        hierarchy = TagHierarchy(
            parent_tag_id=parent_id,
            child_tag_id=child_id,
            relationship_type=relationship_type
        )
        
        self.db.add(hierarchy)
        try:
            self.db.commit()
            logger.info(f"Added tag hierarchy relationship: Parent '{parent.name}' -> Child '{child.name}'")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding tag hierarchy relationship: {str(e)}")
            return False
            
    def remove_parent_child_relationship(self, parent_id: UUID, child_id: UUID) -> bool:
        """
        Remove a parent-child relationship between two tags.
        
        Args:
            parent_id: ID of the parent tag
            child_id: ID of the child tag
            
        Returns:
            True if relationship was removed successfully, False if the relationship doesn't exist
            or if either tag doesn't exist
        """
        # Check that both tags exist
        parent = self.get(parent_id)
        child = self.get(child_id)
        if not parent or not child:
            logger.error(f"Cannot remove relationship: Parent or child tag doesn't exist. Parent ID: {parent_id}, Child ID: {child_id}")
            return False
            
        # Find the relationship
        hierarchy = self.db.query(TagHierarchy).filter(
            and_(
                TagHierarchy.parent_tag_id == parent_id,
                TagHierarchy.child_tag_id == child_id
            )
        ).first()
        
        if not hierarchy:
            logger.error(f"Cannot remove relationship: Relationship doesn't exist. Parent: {parent.name}, Child: {child.name}")
            return False
            
        # Remove the relationship
        try:
            self.db.delete(hierarchy)
            self.db.commit()
            logger.info(f"Removed tag hierarchy relationship: Parent '{parent.name}' -> Child '{child.name}'")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing tag hierarchy relationship: {str(e)}")
            return False
            
    def would_create_cycle(self, parent_id: UUID, child_id: UUID) -> bool:
        """
        Check if adding a parent-child relationship would create a cycle in the tag hierarchy.
        
        Args:
            parent_id: ID of the parent tag
            child_id: ID of the child tag
            
        Returns:
            True if relationship would create a cycle, False otherwise
        """
        # Delegate to the TagHierarchy static method which implements the cycle check logic
        from app.db.models.tag_hierarchy import TagHierarchy
        return TagHierarchy.check_for_cycle(self.db, parent_id, child_id)
        
    def find_cycle_path(self, parent_id: UUID, child_id: UUID) -> List[UUID]:
        """
        Find and return the path of a cycle that would be created by adding a parent-child relationship.
        
        Args:
            parent_id: ID of the parent tag
            child_id: ID of the child tag
            
        Returns:
            List of tag IDs that form the cycle, or empty list if no cycle would be created
        """
        # Immediate cycle check
        if parent_id == child_id:
            return [parent_id, child_id]
            
        # Set to track visited nodes to avoid infinite loops
        visited = set()
        # Current path being explored
        path = []
        # Complete cycle path if found
        cycle_path = []
        
        def dfs(current_id, target_id):
            """Depth-first search to find a path from current_id to target_id"""
            nonlocal cycle_path
            
            # If we've found the target, we've detected a cycle
            if current_id == target_id:
                cycle_path = path + [current_id]
                return True
                
            # Skip if already visited
            if current_id in visited:
                return False
                
            # Mark as visited and add to current path
            visited.add(current_id)
            path.append(current_id)
            
            # Get all parent tags of the current tag
            parents = self.get_parent_tags(current_id)
            
            # Check if any parent completes a path to the target
            for parent in parents:
                if dfs(parent.id, target_id):
                    return True
                    
            # Backtrack: remove from path if no cycle found
            path.pop()
            return False
        
        # The cycle would be created by making child_id -> parent_id relationship
        # So check if there's already a path from parent_id -> child_id
        dfs(parent_id, child_id)
        
        return cycle_path
    
    def _is_ancestor(self, potential_ancestor_id: UUID, tag_id: UUID, visited: Set[UUID] = None) -> bool:
        """
        Recursive function to check if potential_ancestor_id is an ancestor of tag_id.
        
        Args:
            potential_ancestor_id: ID of the potential ancestor tag
            tag_id: ID of the tag to check
            visited: Set of already visited tag IDs to prevent infinite recursion
            
        Returns:
            True if potential_ancestor_id is an ancestor of tag_id, False otherwise
        """
        # Initialize visited set if not provided
        if visited is None:
            visited = set()
            
        # If we've visited this tag before, skip it to prevent infinite recursion
        if tag_id in visited:
            return False
            
        # Add current tag to visited set
        visited.add(tag_id)
        
        # Get all parent IDs of the current tag
        parent_relationships = self.db.query(TagHierarchy).filter(
            TagHierarchy.child_tag_id == tag_id
        ).all()
        
        # Check each parent
        for rel in parent_relationships:
            # If the potential_ancestor_id is a direct parent, return True
            if rel.parent_tag_id == potential_ancestor_id:
                return True
                
            # Recursively check if any parent has the potential_ancestor_id as its ancestor
            if self._is_ancestor(potential_ancestor_id, rel.parent_tag_id, visited):
                return True
                
        # If we've checked all parents and haven't found the potential_ancestor_id, return False
        return False
    
    def get_multi_with_children(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        **kwargs
    ) -> List[Tag]:
        """
        Get multiple tags with their children preloaded, with optional filtering.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (for pagination)
            **kwargs: Filter parameters as field=value pairs
            
        Returns:
            List of Tag instances with children relationships preloaded
        """
        # Start with base query for tags
        query = self.db.query(self.model)
        
        # Apply filters
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                # Handle special case for partial string matching
                if field in ['name', 'description'] and isinstance(value, str):
                    query = query.filter(getattr(self.model, field).ilike(f"%{value}%"))
                else:
                    query = query.filter(getattr(self.model, field) == value)
        
        # Apply pagination and execute query
        tags = query.offset(skip).limit(limit).all()
        
        # For each tag, fetch its children and set as a property
        for tag in tags:
            child_tags = self.get_child_tags(tag.id)
            setattr(tag, "children", child_tags)
            
        return tags
    
    def associate_tag_with_user(self, tag_id: UUID, user_id: UUID) -> bool:
        """
        Associate a tag with a user.
        
        Args:
            tag_id: ID of the tag
            user_id: ID of the user
            
        Returns:
            True if association was successful, False otherwise
        """
        # Implementation depends on how the user-tag relationship is defined
        # Example assuming a many-to-many relationship with User model
        tag = self.get(tag_id)
        if not tag:
            return False
        
        # Assumes a 'users' relationship exists on the Tag model
        from app.db.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        if user not in tag.users:
            tag.users.append(user)
            self.db.commit()
        return True
            
    def create_tag_normalization(self, obj_in: TagNormalizationCreate) -> TagNormalization:
        """
        Create a new tag normalization record.
        
        Args:
            obj_in: Tag normalization data
            
        Returns:
            Created TagNormalization instance
        """
        db_obj = TagNormalization(
            original_name=obj_in.original_name,
            normalized_name=obj_in.normalized_name,
            description=obj_in.description,
            parent_tag_ids=obj_in.parent_tag_ids,
            review_status=obj_in.review_status or TagReviewStatus.pending,
            admin_notes=obj_in.admin_notes,
            source=obj_in.source or TagSource.ai_generated,
            confidence_score=obj_in.confidence_score,
            reviewed_by=obj_in.reviewed_by,
            auto_approved=obj_in.auto_approved or False
        )
        
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def get_tag_normalization(self, id: UUID) -> Optional[TagNormalization]:
        """
        Get a tag normalization record by ID.
        
        Args:
            id: TagNormalization ID
            
        Returns:
            TagNormalization instance or None if not found
        """
        return self.db.query(TagNormalization).filter(TagNormalization.id == id).first()
    
    def get_tag_normalizations(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        review_status: Optional[TagReviewStatus] = None,
        source: Optional[TagSource] = None
    ) -> List[TagNormalization]:
        """
        Get tag normalization records with filtering options.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            review_status: Filter by review status
            source: Filter by source
            
        Returns:
            List of TagNormalization instances
        """
        query = self.db.query(TagNormalization)
        
        if review_status:
            query = query.filter(TagNormalization.review_status == review_status)
            
        if source:
            query = query.filter(TagNormalization.source == source)
        
        return query.offset(skip).limit(limit).all()
        
    def get_pending_normalizations(self, skip: int = 0, limit: int = 100) -> List[TagNormalization]:
        """
        Get all tag normalizations with pending review status.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of TagNormalization instances with pending status
        """
        return self.get_tag_normalizations(
            skip=skip,
            limit=limit,
            review_status=TagReviewStatus.pending
        )
    
    def update_tag_normalization(self, id: UUID, obj_in: TagNormalizationUpdate) -> Optional[TagNormalization]:
        """
        Update a tag normalization record.
        
        Args:
            id: ID of the tag normalization record
            obj_in: Update data
            
        Returns:
            Updated TagNormalization instance, or None if not found
        """
        db_obj = self.get_tag_normalization(id)
        if not db_obj:
            return None
            
        update_data = obj_in.dict(exclude_unset=True)
        
        # Update the record
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        # Update timestamp if review status is changing
        if 'review_status' in update_data:
            db_obj.updated_at = func.now()
            
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def approve_tag_normalization(self, id: UUID, reviewed_by: UUID = None) -> Optional[Tuple[TagNormalization, Tag]]:
        """
        Approve a tag normalization and create the corresponding tag.
        Also associates the newly approved tag with relevant existing problems.
        
        Args:
            id: ID of the tag normalization record
            reviewed_by: ID of the admin who approved the normalization
            
        Returns:
            Tuple of (TagNormalization, Tag) instances if successful, None if not found
        """
        from app.db.models.problem import Problem
        import logging
        logger = logging.getLogger(__name__)
        
        print(f"⭐⭐⭐ TAG APPROVAL: Starting approval process for tag normalization ID {id}")
        
        normalization = self.get_tag_normalization(id)
        if not normalization:
            return None
        
        # Check if the tag is already approved
        is_reapproval = normalization.review_status == TagReviewStatus.approved
            
        # Update normalization status
        normalization.review_status = TagReviewStatus.approved
        normalization.reviewed_at = func.now()
        normalization.reviewed_by = reviewed_by
        
        # Log whether this is a reapproval or first-time approval
        if is_reapproval:
            logger.info(f"Reapproving tag normalization {id}")
        else:
            logger.info(f"Approving tag normalization {id} for the first time")
        
        # Check if a tag with this name already exists
        existing_tag = self.get_by_name_case_insensitive(normalization.normalized_name)
        
        # Which tag will be used - either existing or new
        tag_to_use = None
        
        # If tag already exists, just associate it with normalization
        if existing_tag:
            normalization.approved_tag_id = existing_tag.id
            tag_to_use = existing_tag
        else:
            # Otherwise create new tag from normalization
            new_tag = Tag(
                name=normalization.normalized_name,
                description=normalization.description,
                tag_type="concept"  # Default to concept type for compatibility with test environment
            )
            
            self.db.add(new_tag)
            self.db.flush()  # Get ID without committing
            
            # Add parent relationships if specified
            if normalization.parent_tag_ids:
                for parent_id in normalization.parent_tag_ids:
                    # Create the relationship
                    self.add_parent_child_relationship(parent_id, new_tag.id)
            
            # Link the normalization to the new tag
            normalization.approved_tag_id = new_tag.id
            tag_to_use = new_tag
        
        # Associate the tag with relevant problems
        try:
            # Get the normalized name to search for in problems
            tag_name = tag_to_use.name
            logger.info(f"🔍 TAG ASSOCIATION: Attempting to associate tag '{tag_name}' with relevant problems")
            logger.info(f"Associating tag '{tag_name}' with relevant problems")
            
            # Search for problems containing the tag name in title
            problems_with_tag_in_title = self.db.query(Problem).filter(
                Problem.title.ilike(f"%{tag_name}%")
            ).all()
            
            # Also search in description and problem_metadata
            problems_with_tag_in_content = self.db.query(Problem).filter(
                or_(
                    Problem.description.ilike(f"%{tag_name}%"),
                    cast(Problem.problem_metadata, String).ilike(f"%{tag_name}%")
                )
            ).all()
            
            # Combine and deduplicate results
            all_relevant_problems = set(problems_with_tag_in_title + problems_with_tag_in_content)
            
            # Associate tag with each relevant problem            
            association_count = 0
            already_associated_count = 0
            for problem in all_relevant_problems:
                # Check if tag is already associated with the problem
                if tag_to_use not in problem.tags:
                    problem.tags.append(tag_to_use)
                    association_count += 1
                    logger.info(f"➕ TAG ASSOCIATION: Added tag to problem '{problem.title[:30]}...' (ID: {problem.id})")
                else:
                    already_associated_count += 1
                    logger.info(f"⏩ TAG ASSOCIATION: Tag already on problem '{problem.title[:30]}...' (ID: {problem.id})")
                # After the loop completes
            logger.info(f"✅ TAG ASSOCIATION: Successfully associated tag with {association_count} problems, {already_associated_count} were already associated")
            logger.info(f"Associated tag '{tag_name}' with {association_count} problems")
        except Exception as e:
            logger.error(f"❌ TAG ASSOCIATION ERROR: {str(e)}")
            logger.error(f"Error associating tag with problems: {str(e)}")
        
        # Commit the transaction
        self.db.commit()        
        self.db.refresh(normalization)
        
        if existing_tag:
            return normalization, existing_tag
        else:
            self.db.refresh(tag_to_use)
            return normalization, tag_to_use
    
    def reject_tag_normalization(self, id: UUID, admin_notes: str = None, reviewed_by: UUID = None) -> Optional[TagNormalization]:
        """
        Reject a tag normalization.
        
        Args:
            id: ID of the tag normalization record
            admin_notes: Notes explaining the rejection
            reviewed_by: ID of the admin who rejected the normalization
            
        Returns:
            Updated TagNormalization instance, or None if not found
        """
        normalization = self.get_tag_normalization(id)
        if not normalization:
            return None
            
        normalization.review_status = TagReviewStatus.rejected
        normalization.reviewed_at = func.now()
        normalization.reviewed_by = reviewed_by
        
        if admin_notes:
            normalization.admin_notes = admin_notes
            
        self.db.commit()
        self.db.refresh(normalization)
        return normalization
        
    def find_similar_tag_normalizations(self, name: str, threshold: float = 0.8) -> List[TagNormalization]:
        """
        Find tag normalizations with similar names.
        
        Args:
            name: Name to search for
            threshold: Similarity threshold (default: 0.8)
            
        Returns:
            List of TagNormalization instances with similar names
        """
        # For exact matches or case-insensitive matches
        return self.db.query(TagNormalization).filter(
            func.lower(TagNormalization.original_name) == func.lower(name)
        ).all()
    
    def detect_hierarchy_cycles(self) -> List[List[UUID]]:
        """
        Detect cycles in the tag hierarchy.
        
        Returns:
            List of cycles, where each cycle is a list of tag IDs forming a cycle
        """
        # Get all tag IDs
        tag_ids = [tag.id for tag in self.db.query(Tag.id).all()]
        
        cycles = []
        
        # Check each tag as a potential starting point for a cycle
        for tag_id in tag_ids:
            cycle = self._detect_cycle_from_tag(tag_id)
            if cycle and cycle not in cycles:
                cycles.append(cycle)
                
        return cycles
    
    def _detect_cycle_from_tag(self, start_tag_id: UUID) -> Optional[List[UUID]]:
        """
        Detect a cycle starting from the given tag.
        
        Args:
            start_tag_id: ID of the tag to start from
            
        Returns:
            List of tag IDs forming a cycle, or None if no cycle is found
        """
        # Use depth-first search to detect cycles
        path = []  # Current path we're exploring
        visited = set()  # All nodes we've visited
        
        def dfs(tag_id: UUID) -> Optional[List[UUID]]:
            # If we've seen this tag in the current path, we found a cycle
            if tag_id in path:
                # Extract the cycle (from the tag to itself)
                cycle_start_idx = path.index(tag_id)
                return path[cycle_start_idx:] + [tag_id]
                
            # If we've already explored this tag and found no cycles, skip it
            if tag_id in visited:
                return None
                
            # Mark tag as visited and add to current path
            visited.add(tag_id)
            path.append(tag_id)
            
            # Get all child tags
            child_ids = [
                rel.child_tag_id for rel in 
                self.db.query(TagHierarchy.child_tag_id)
                .filter(TagHierarchy.parent_tag_id == tag_id)
                .all()
            ]
            
            # Explore each child
            for child_id in child_ids:
                cycle = dfs(child_id)
                if cycle:
                    return cycle
                    
            # Backtrack
            path.pop()
            return None
            
        return dfs(start_tag_id)
        
    def update_tag(self, id: UUID, update_data: Dict[str, Any]) -> Optional[Tag]:
        """
        Update a tag with new data.
        
        Args:
            id: ID of the tag to update
            update_data: Dictionary of fields to update
            
        Returns:
            Updated Tag instance if successful, None if not found
        """
        db_obj = self.db.query(self.model).filter(self.model.id == id).first()
        if not db_obj:
            return None
            
        # Update fields
        for key, value in update_data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
                
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        
        return db_obj
            
    def associate_tag_with_problem(self, tag_id: UUID, problem_id: UUID) -> bool:
        """
        Associate a tag with a problem.
        
        Args:
            tag_id: ID of the tag
            problem_id: ID of the problem
            
        Returns:
            True if association was successful, False otherwise
        """
        # Check that tag exists
        tag_count = self.db.query(self.model).filter(self.model.id == tag_id).count()
        if not tag_count:
            return False
        
        # Check that problem exists
        from app.db.models.problem import Problem
        problem_count = self.db.query(Problem).filter(Problem.id == problem_id).count()
        if not problem_count:
            return False
        
        # Get objects
        tag = self.get(tag_id)
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        
        # Check if association already exists
        if tag in problem.tags:
            return True
            
        # Create association
        problem.tags.append(tag)
        self.db.commit()
        return True
    
    def delete(self, id: UUID) -> bool:
        """
        Delete a tag by ID and remove all its hierarchy relationships.
        
        Args:
            id: ID of the tag to delete
            
        Returns:
            True if tag was deleted, False if not found
        """
        # Start a transaction
        db_obj = self.db.query(self.model).filter(self.model.id == id).first()
        if not db_obj:
            return False
            
        try:
            # First remove all hierarchy relationships involving this tag
            self.db.query(TagHierarchy).filter(
                or_(
                    TagHierarchy.parent_tag_id == id,
                    TagHierarchy.child_tag_id == id
                )
            ).delete()
            
            # Then delete the tag itself
            self.db.delete(db_obj)
            self.db.commit()
            
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting tag: {str(e)}")
            return False
