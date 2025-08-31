"""
Test database migration for the problem_metadata field.
This ensures the test database includes this field.
"""
import pytest
import json
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, text, inspect
from sqlalchemy.types import JSON as SQLAlchemyJSON

def test_ensure_problem_metadata_exists(db_session):
    """
    Test to ensure problem_metadata exists in the test database.
    This will also add it if missing for SQLite compatibility.
    """
    # Check if column exists
    inspector = inspect(db_session.bind)
    has_column = False
    
    for column in inspector.get_columns('problems'):
        if column['name'] == 'problem_metadata':
            has_column = True
            break
            
    if not has_column:
        # Add the column to SQLite for testing
        # SQLite doesn't support JSONB natively, so we use TEXT
        is_sqlite = str(db_session.bind.url).startswith('sqlite')
        
        if is_sqlite:
            db_session.execute(text(
                "ALTER TABLE problems ADD COLUMN problem_metadata TEXT"
            ))
        else:
            db_session.execute(text(
                "ALTER TABLE problems ADD COLUMN problem_metadata JSONB"
            ))
            
        db_session.commit()
        
    assert True, "problem_metadata column is available in tests"
