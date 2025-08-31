"""
Association tables for many-to-many relationships.
These tables need to be defined separately to avoid circular imports.
"""

from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

# Association table for User-Tag many-to-many relationship
user_tags = Table(
    "user_tags",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"))
)

# Association table for Problem-Tag many-to-many relationship
problem_tags = Table(
    "problem_tags",
    Base.metadata,
    Column("problem_id", UUID(as_uuid=True), ForeignKey("problems.id")),
    Column("tag_id", UUID(as_uuid=True), ForeignKey("tags.id"))
)
