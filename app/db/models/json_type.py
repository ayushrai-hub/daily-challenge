"""
SQLAlchemy JSON type that works with both PostgreSQL and SQLite.

This module defines a custom JSON type that uses JSONB for PostgreSQL
and Text/JSON for SQLite to ensure compatibility across environments.
"""
import json
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.dialects.postgresql import JSONB

class JSONType(TypeDecorator):
    """
    Platform-independent JSON type.
    
    Uses PostgreSQL's native JSONB type when available, 
    otherwise uses TEXT and serializes/deserializes JSON.
    """
    
    impl = TEXT  # Default implementation uses TEXT
    cache_ok = True
    
    def load_dialect_impl(self, dialect):
        """Load dialect-specific implementation of type."""
        if dialect.name == 'postgresql':
            # Use native JSONB for PostgreSQL
            return dialect.type_descriptor(JSONB())
        else:
            # Use TEXT for SQLite and others
            return dialect.type_descriptor(self.impl)
    
    def process_bind_param(self, value, dialect):
        """Process value when binding to statement."""
        if value is None:
            return None
        
        if dialect.name == 'postgresql':
            # PostgreSQL can handle dictionaries natively with JSONB
            return value
        else:
            # For SQLite and others, convert to JSON string
            return json.dumps(value)
    
    def process_result_value(self, value, dialect):
        """Process value when retrieving from database."""
        if value is None:
            return None
            
        if dialect.name == 'postgresql':
            # PostgreSQL JSONB already returns a dict
            return value
        else:
            # For SQLite, parse the JSON string
            try:
                return json.loads(value)
            except (ValueError, TypeError):
                return {}  # Return empty dict if invalid JSON
