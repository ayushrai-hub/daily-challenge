"""03_create_content_sources_table

Revision ID: 03_create_content_sources
Revises: 02_create_tags
Create Date: 2025-05-03 12:58:26.478284

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '03_create_content_sources'
down_revision = '02_create_tags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create content_sources table
    op.create_table(
        'content_sources',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_platform', sa.Enum('stackoverflow', 'gh_issues', 'blog', 'reddit', 'hackernews', 'dev_to', 'custom', 
                                         name='sourceplatform'), nullable=False),
        sa.Column('source_identifier', sa.String(), nullable=False),
        sa.Column('raw_data', JSONB(), nullable=True),
        sa.Column('processed_text', sa.Text(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('processing_status', sa.Enum('pending', 'processed', 'failed', name='processingstatus'), 
                  server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Index on source platform for filtering
    op.create_index(op.f('ix_content_sources_source_platform'), 'content_sources', ['source_platform'], unique=False)
    # Index on source_identifier for lookups
    op.create_index(op.f('ix_content_sources_source_identifier'), 'content_sources', ['source_identifier'], unique=False)
    # Composite index for platform+identifier uniqueness
    op.create_index(op.f('ix_content_sources_platform_identifier'), 'content_sources', 
                   ['source_platform', 'source_identifier'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_content_sources_platform_identifier'), table_name='content_sources')
    op.drop_index(op.f('ix_content_sources_source_identifier'), table_name='content_sources')
    op.drop_index(op.f('ix_content_sources_source_platform'), table_name='content_sources')
    op.drop_table('content_sources')
    
    # Drop enum types explicitly
    op.execute('DROP TYPE IF EXISTS sourceplatform;')
    op.execute('DROP TYPE IF EXISTS processingstatus;')
