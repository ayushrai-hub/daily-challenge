"""
Add created_at and updated_at timestamps to tag_hierarchy table

Revision ID: 08b_add_timestamps_to_tag_hierarchy
Revises: 08a_7f8d3b9e
Create Date: 2025-05-13

This migration adds timestamp tracking to tag hierarchy relationships.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = '08b_1a2b3c4d'  # Unique revision ID
down_revision = '08a_7f8d3b9e'  # Points to the previous migration (tag hierarchy refactoring)
branch_labels = None
depends_on = None


def upgrade():
    # Add created_at column with default NOW()
    op.add_column('tag_hierarchy',
        sa.Column('created_at', sa.DateTime(timezone=True), 
                 nullable=False, 
                 server_default=sa.func.now())
    )
    
    # Add updated_at column with default NOW() and auto-update on row update
    op.add_column('tag_hierarchy',
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                 nullable=False, 
                 server_default=sa.func.now(),
                 server_onupdate=sa.func.now())
    )


def downgrade():
    # Remove the timestamp columns
    op.drop_column('tag_hierarchy', 'updated_at')
    op.drop_column('tag_hierarchy', 'created_at')
