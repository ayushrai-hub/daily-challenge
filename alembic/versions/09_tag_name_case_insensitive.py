"""
Update tag name constraint to be case-insensitive

Revision ID: 09_tag_name_case_insensitive
Revises: 08b_add_timestamps_to_tag_hierarchy
Create Date: 2025-05-13

This migration:
1. Removes the existing unique constraint on tags.name
2. Creates a new case-insensitive unique index on lower(name)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '09_tag_name_case_insensitive'
down_revision = '08b_1a2b3c4d'  # Reference the correct 08b revision ID
branch_labels = None
depends_on = None

def upgrade():
    # The unique constraint on 'name' is implemented as a unique index named 'ix_tags_name'
    # First, drop the existing unique index
    conn = op.get_bind()
    
    # Drop the existing unique index on name
    try:
        op.drop_index('ix_tags_name', table_name='tags')
        print("Dropped existing unique index 'ix_tags_name'")
    except Exception as e:
        print(f"Could not drop index 'ix_tags_name': {e}")
    
    # Create a non-unique index on name for regular lookups
    try:
        op.create_index('ix_tags_name', 'tags', ['name'], unique=False)
        print("Created non-unique index 'ix_tags_name'")
    except Exception as e:
        print(f"Could not create non-unique index: {e}")
    
    # Create a case-insensitive unique index
    try:
        # Check if the index already exists
        result = conn.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'ix_tags_name_lower'").fetchone()
        if not result:
            op.execute("CREATE UNIQUE INDEX ix_tags_name_lower ON tags (lower(name));")
            print("Created case-insensitive unique index 'ix_tags_name_lower'")
        else:
            print("Case-insensitive index 'ix_tags_name_lower' already exists")
    except Exception as e:
        print(f"Error with case-insensitive index: {e}")


def downgrade():
    # Drop the case-insensitive index
    op.drop_index('ix_tags_name_lower', table_name='tags')
    
    # Drop the non-unique index
    op.drop_index('ix_tags_name', table_name='tags')
    
    # Recreate the original unique constraint
    op.create_index('ix_tags_name', 'tags', ['name'], unique=True)
    op.create_unique_constraint('tags_name_key', 'tags', ['name'])
