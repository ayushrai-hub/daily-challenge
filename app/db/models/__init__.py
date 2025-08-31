"""
Models package initialization.
Imports all models to ensure they're registered with SQLAlchemy.
Import order is important to avoid circular dependencies.
"""

# First, import the tag patch to fix relationship mapping issues
# This must be imported before any other models
from app.db.models.tag_patch import *

# First, import association tables (no dependencies)
from app.db.models.association_tables import user_tags, problem_tags

# Then import tag hierarchy table which is used in self-referential relationships
from app.db.models.tag_hierarchy import TagHierarchy

# Base models (minimal dependencies)
from app.db.models.base_model import BaseModel
from app.db.models.user import User
from app.db.models.tag import Tag
from app.db.models.content_source import ContentSource

# Models with dependencies on basic models
from app.db.models.problem import Problem
from app.db.models.delivery_log import DeliveryLog
from app.db.models.email_queue import EmailQueue

# Make models available at the package level
__all__ = [
    'BaseModel',
    'User',
    'Tag',
    'TagHierarchy',
    'ContentSource',
    'Problem',
    'DeliveryLog',
    'EmailQueue',
    'user_tags',
    'problem_tags',
]