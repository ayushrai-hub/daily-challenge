from sqlalchemy import Column, String, Enum, Boolean, Text, ForeignKey, Table, Index, func
from sqlalchemy.orm import relationship, foreign, remote, backref
from sqlalchemy.dialects.postgresql import UUID
from enum import Enum as PyEnum

from app.db.models.base_model import BaseModel
from app.db.models.association_tables import user_tags, problem_tags
from app.db.models.tag_hierarchy import TagHierarchy
from app.core.logging import get_logger

logger = get_logger()

class TagType(PyEnum):
    language = "language"           # Programming language
    framework = "framework"         # Framework or library
    concept = "concept"             # CS or programming concept
    domain = "domain"               # Business or application domain
    skill_level = "skill_level"     # Beginner, intermediate, advanced etc.
    tool = "tool"                   # Development tool or platform
    topic = "topic"                 # General categorization topic

class Tag(BaseModel):
    __tablename__ = "tags"
    __table_args__ = {
        'extend_existing': True
    }

    name = Column(String, nullable=False, index=True)
    
    # Create a case-insensitive unique index on the lowercase version of the name
    # This will be created by the migration script we wrote separately
    description = Column(Text, nullable=True)
    tag_type = Column(Enum(TagType), nullable=True)  # Optional classification
    is_featured = Column(Boolean, default=False, nullable=False)  # Featured in UI/recommendations
    is_private = Column(Boolean, default=False, nullable=False)   # Internal use only, not exposed to users
    
    # Use imported association tables directly
    users = relationship("User", secondary=user_tags, back_populates="tags", lazy="selectin")
    problems = relationship("Problem", secondary=problem_tags, back_populates="tags", lazy="selectin")
    
    # Properly configured many-to-many self-referential relationship for parent-child tags
    parents = relationship(
        "Tag",
        secondary=TagHierarchy.__table__,
        primaryjoin="Tag.id == foreign(TagHierarchy.child_tag_id)",
        secondaryjoin="Tag.id == foreign(TagHierarchy.parent_tag_id)",
        backref=backref(
            "children", 
            lazy="selectin",
            overlaps="parents"
        ),
        lazy="selectin",
        viewonly=True,  # Ensure this is viewonly to avoid SQLAlchemy conflicts
        collection_class=set,
        overlaps="children"  # Explicitly handle the overlapping collection
    )
    
    def __repr__(self):
        return f"<Tag id={self.id} name='{self.name}'>"
        
    def __str__(self):
        return self.name
