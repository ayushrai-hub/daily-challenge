"""
Add problem_metadata JSONB column to problems table

Revision ID: 10_add_metadata_to_problems
Revises: 09_tag_name_case_insensitive
Create Date: 2025-05-14

This migration adds a problem_metadata JSONB column to the problems table to store
additional information related to problems, including pending tag suggestions.
Avoiding 'metadata' as it's a reserved name in SQLAlchemy's Declarative API.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic
revision = '10_add_metadata_to_problems'
down_revision = '09_tag_name_case_insensitive'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add problem_metadata column to problems table using JSONB for efficient storage and queries
    op.add_column('problems', sa.Column('problem_metadata', JSONB, nullable=True))
    
    # Add an index on the problem_metadata column for more efficient queries
    # This uses GIN (Generalized Inverted Index) which works well for JSONB
    op.create_index('ix_problems_problem_metadata_gin', 'problems', ['problem_metadata'], 
                    postgresql_using='gin')


def downgrade() -> None:
    # Remove the index first, then the column
    op.drop_index('ix_problems_problem_metadata_gin', table_name='problems')
    op.drop_column('problems', 'problem_metadata')
