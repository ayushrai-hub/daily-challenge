"""04_create_problems_table

Revision ID: 04_create_problems
Revises: 03_create_content_sources
Create Date: 2025-05-03 13:02:41.641661

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '04_create_problems'
down_revision = '03_create_content_sources'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create problems table
    op.create_table(
        'problems',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('solution', sa.Text(), nullable=True),
        sa.Column('difficulty_level', sa.Enum('easy', 'medium', 'hard', name='difficultylevel'), 
                  server_default='medium', nullable=False),
        sa.Column('vetting_tier', sa.Enum('tier1_manual', 'tier2_ai', 'tier3_needs_review', name='vettingtier'), 
                  server_default='tier3_needs_review', nullable=False),
        sa.Column('status', sa.Enum('draft', 'approved', 'archived', 'pending', name='problemstatus'), 
                  server_default='draft', nullable=False),
        sa.Column('content_source_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_source_id'], ['content_sources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create problem_tags association table
    op.create_table(
        'problem_tags',
        sa.Column('problem_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('problem_id', 'tag_id')
    )
    
    # Add indexes
    # Title index for searching
    op.create_index(op.f('ix_problems_title'), 'problems', ['title'], unique=False)
    # Status index for filtering by status
    op.create_index(op.f('ix_problems_status'), 'problems', ['status'], unique=False)
    # Vetting tier index for filtering
    op.create_index(op.f('ix_problems_vetting_tier'), 'problems', ['vetting_tier'], unique=False)
    # Content source index for joins
    op.create_index(op.f('ix_problems_content_source_id'), 'problems', ['content_source_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_problems_content_source_id'), table_name='problems')
    op.drop_index(op.f('ix_problems_vetting_tier'), table_name='problems')
    op.drop_index(op.f('ix_problems_status'), table_name='problems')
    op.drop_index(op.f('ix_problems_title'), table_name='problems')
    
    # Drop tables
    op.drop_table('problem_tags')
    op.drop_table('problems')
    
    # Drop enum types explicitly to ensure cleanup
    op.execute('DROP TYPE IF EXISTS vettingtier;')
    op.execute('DROP TYPE IF EXISTS difficultylevel;')
    op.execute('DROP TYPE IF EXISTS problemstatus;')
