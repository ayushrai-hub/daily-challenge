"""06c_enhance_content_source_model

Revision ID: 06c_enhance_content_source_model
Revises: 06b_enhance_problem_model
Create Date: 2025-05-03 18:28:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, ARRAY

# revision identifiers, used by Alembic.
revision = '06c_enhance_content_source_model'
down_revision = '06b_enhance_problem_model'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip SourcePlatform enum changes since they're already in the base migration
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_enums = inspector.get_enums()
    
    # Check if the sourceplatform enum exists
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'sourceplatform':
            enum_exists = True
            break
    
    if not enum_exists:
        # Create the enum only if it doesn't exist
        sourceplatform = ENUM('stackoverflow', 'gh_issues', 'blog', 'reddit', 'hackernews', 'dev_to', 'custom',
                             name='sourceplatform', create_type=True)
        sourceplatform.create(op.get_bind(), checkfirst=True)
    
    # Skip processing status enum and column operations
    # These are already handled in 03_create_content_sources_table.py
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'processingstatus':
            enum_exists = True
            break
    
    if not enum_exists:
        # Create the enum only if it doesn't exist
        processingstatus = ENUM('pending', 'processing', 'completed', 'failed',
                               name='processingstatus', create_type=True)
        processingstatus.create(op.get_bind(), checkfirst=True)
    
    # Check which columns already exist in the content_sources table
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('content_sources')]
    
    # Only add columns that don't already exist
    if 'source_url' not in existing_columns:
        op.add_column('content_sources', sa.Column('source_url', sa.String(), nullable=True))
    
    if 'source_title' not in existing_columns:
        op.add_column('content_sources', sa.Column('source_title', sa.String(), nullable=True))
    
    if 'source_tags' not in existing_columns:
        op.add_column('content_sources', sa.Column('source_tags', ARRAY(sa.String()), nullable=True))
    
    if 'processed_text' not in existing_columns:
        op.add_column('content_sources', sa.Column('processed_text', sa.Text(), nullable=True))
    
    if 'processed_at' not in existing_columns:
        op.add_column('content_sources', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'ingested_at' not in existing_columns:
        op.add_column('content_sources', sa.Column('ingested_at', sa.DateTime(timezone=True), 
                                               server_default=sa.func.now(), nullable=False))


def downgrade() -> None:
    # Only drop the columns we actually added in the upgrade method
    op.drop_column('content_sources', 'ingested_at')
    op.drop_column('content_sources', 'processed_at')
    op.drop_column('content_sources', 'processed_text')
    op.drop_column('content_sources', 'source_tags')
    op.drop_column('content_sources', 'source_title')
    op.drop_column('content_sources', 'source_url')
    
    # Skip dropping processing_status since we didn't add it in the upgrade
    # Skip dropping enums since we didn't modify them in the upgrade
