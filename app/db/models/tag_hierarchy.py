"""
Tag hierarchy model to support multiple parent-child relationships between tags.
This allows a tag to belong to multiple categories simultaneously.
"""
from sqlalchemy import Column, ForeignKey, String, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.models.base_model import BaseModel
from app.core.logging import get_logger

logger = get_logger()


class TagHierarchy(BaseModel):
    """
    Model representing the many-to-many relationship between tags.
    Allows a tag to have multiple parents and multiple children.
    """
    __tablename__ = "tag_hierarchy"
    
    # Define constraints at the table level  
    __table_args__ = (
        # Unique constraint to prevent duplicate parent-child pairs
        UniqueConstraint('parent_tag_id', 'child_tag_id', name='uq_tag_hierarchy_parent_child'),
        # Index to speed up parent-child lookups
        Index('ix_tag_hierarchy_parent_id', 'parent_tag_id'),
        Index('ix_tag_hierarchy_child_id', 'child_tag_id'),
        {'extend_existing': True}
    )
    
    # We don't need the id column from BaseModel as we have a composite primary key
    # The id field is explicitly removed and replaced with a composite primary key
    id = None
    
    # These columns form our composite primary key
    parent_tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    child_tag_id = Column(UUID(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    relationship_type = Column(String, nullable=True)  # Optional classification of relationship
    
    # Add timestamp fields
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<TagHierarchy parent_id={self.parent_tag_id} child_id={self.child_tag_id}>"
        
    @staticmethod
    def check_for_cycle(db_session, parent_id, child_id):
        """
        Check if adding this relationship would create a cycle in the tag hierarchy.
        
        This method checks for three types of cycles:
        1. Self-reference: A tag cannot be its own parent
        2. Direct cycle: A↔B (if B is already a parent of A, A cannot be a parent of B)
        3. Transitive cycle: A→B→C→...→A (complex cycles in the hierarchy)
        
        Args:
            db_session: SQLAlchemy database session
            parent_id: ID of the parent tag
            child_id: ID of the child tag
            
        Returns:
            bool: True if this would create a cycle, False otherwise
        """
        from app.core.logging import get_logger
        logger = get_logger()
        
        logger.info(f"Checking for cycle between parent={parent_id} and child={child_id}")
        
        # 1. Self-reference check (A→A)
        if parent_id == child_id:
            logger.warning(f"Self-reference cycle detected: {parent_id} cannot be its own parent")
            return True
        
        # 2. Direct cycle check (A→B and B→A)
        # Check if the proposed child is already a parent of the proposed parent
        direct_cycle = db_session.query(TagHierarchy).filter(
            TagHierarchy.parent_tag_id == child_id,
            TagHierarchy.child_tag_id == parent_id
        ).first() is not None
        
        if direct_cycle:
            logger.warning(f"Direct cycle detected: {child_id} is already a parent of {parent_id}")
            return True
        
        # 3. Transitive cycle check (A→B→C→...→A)
        # If the child is already an ancestor of the parent anywhere in the hierarchy
        # (or if adding this edge would create a path from child back to parent)
        visited = set()
        cycle_path = []
        
        def is_ancestor(current_id, target_id, path=None):
            """Check if current_id is an ancestor of target_id in the hierarchy."""
            if path is None:
                path = []
                
            # Found the target - cycle detected
            if current_id == target_id:
                cycle_path.extend(path + [current_id])
                logger.warning(f"Cycle detected! Path: {' → '.join(map(str, cycle_path))}")
                return True
                
            # Already visited this node, avoid infinite recursion
            if current_id in visited:
                return False
                
            # Mark as visited
            visited.add(current_id)
            current_path = path + [current_id]
            
            # Get all parents of the current node
            parents = db_session.query(TagHierarchy.parent_tag_id)\
                .filter(TagHierarchy.child_tag_id == current_id)\
                .all()
                
            # Check if any parent leads to a cycle
            for parent in parents:
                parent_id = parent[0]
                if is_ancestor(parent_id, target_id, current_path):
                    return True
                    
            return False
        
        # Check if the child is an ancestor of the parent (would create a cycle)
        # This means: would there be a path from child back to parent?
        result = is_ancestor(child_id, parent_id)
        
        if result:
            logger.warning(f"Transitive cycle detected between {parent_id} and {child_id}")
            
        return result
