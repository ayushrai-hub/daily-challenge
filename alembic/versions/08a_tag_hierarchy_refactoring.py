"""
Tag hierarchy refactoring to support multi-parent relationships and admin review of AI-generated tags

Revision ID: 08a_tag_hierarchy_refactoring
Revises: custom_add_verification_metrics
Create Date: 2025-05-13

This migration:
1. Creates a tag_hierarchy junction table for many-to-many parent-child tag relationships
2. Creates a tag_normalizations table for tracking and approving AI-generated tags
3. Migrates existing parent-child relationships to the new structure
4. Removes the old parent_tag_id column from the tags table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column, text
import uuid

# revision identifiers, used by Alembic
revision = '08a_7f8d3b9e'  # Fixed revision ID with numeric suffix
down_revision = 'custom_add_verification_metrics'  # This points to the previous migration
branch_labels = None
depends_on = None

def upgrade():
    # Create tag_hierarchy table
    op.create_table(
        'tag_hierarchy',
        sa.Column('parent_tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relationship_type', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['parent_tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['child_tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('parent_tag_id', 'child_tag_id')
    )
    
    # Create indexes for improved query performance
    # Index for efficient lookups of children by parent
    op.create_index('ix_tag_hierarchy_parent_tag_id', 'tag_hierarchy', ['parent_tag_id'])
    
    # Index for efficient lookups of parents by child
    op.create_index('ix_tag_hierarchy_child_tag_id', 'tag_hierarchy', ['child_tag_id'])
    
    # Composite index for relationship type lookups 
    op.create_index('ix_tag_hierarchy_rel_type', 'tag_hierarchy', ['relationship_type'])
    
    # Index to optimize common queries for both direction relationships with type
    op.create_index('ix_tag_hierarchy_full', 'tag_hierarchy', 
                    ['parent_tag_id', 'child_tag_id', 'relationship_type'])
    
    # Let SQLAlchemy handle the enum creation automatically when creating the tables
    # Define the enum types programmatically instead of with direct SQL
    print("Letting SQLAlchemy handle enum creation during table creation")
    tag_review_status_type = sa.Enum('pending', 'approved', 'rejected', 'modified', name='tag_review_status')
    tag_source_type = sa.Enum('ai_generated', 'user_created', 'admin_created', 'imported', name='tag_source')
    
    # Create tag_normalizations table
    op.create_table(
        'tag_normalizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('original_name', sa.String(), nullable=False),
        sa.Column('normalized_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_tag_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('review_status', tag_review_status_type, nullable=False, server_default='pending'),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('source', tag_source_type, nullable=False, server_default='ai_generated'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_tag_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auto_approved', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['approved_tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for tag_normalizations table
    op.create_index(op.f('ix_tag_normalizations_original_name'), 'tag_normalizations', ['original_name'], unique=False)
    op.create_index(op.f('ix_tag_normalizations_normalized_name'), 'tag_normalizations', ['normalized_name'], unique=False)
    
    # Index for review status - critical for admin review queries
    op.create_index(op.f('ix_tag_normalizations_review_status'), 'tag_normalizations', ['review_status'], unique=False)
    
    # Index for source - helps filter tags by source
    op.create_index(op.f('ix_tag_normalizations_source'), 'tag_normalizations', ['source'], unique=False)
    
    # Index for approved tag lookup
    op.create_index(op.f('ix_tag_normalizations_approved_tag_id'), 'tag_normalizations', ['approved_tag_id'], unique=False)
    
    # Composite index for common filtering patterns
    op.create_index(op.f('ix_tag_normalizations_status_source'), 'tag_normalizations', ['review_status', 'source'], unique=False)
    
    # Migrate existing parent-child relationships to the tag_hierarchy table
    # Define tables for the data migration
    tags_table = table(
        'tags',
        column('id', postgresql.UUID(as_uuid=True)),
        column('parent_tag_id', postgresql.UUID(as_uuid=True))
    )
    
    tag_hierarchy_table = table(
        'tag_hierarchy',
        column('parent_tag_id', postgresql.UUID(as_uuid=True)),
        column('child_tag_id', postgresql.UUID(as_uuid=True)),
        column('relationship_type', sa.String)
    )
    
    # Insert existing parent-child relationships into tag_hierarchy
    conn = op.get_bind()
    results = conn.execute(
        sa.select(tags_table.c.id, tags_table.c.parent_tag_id)
        .where(tags_table.c.parent_tag_id.isnot(None))
    )
    
    for row in results:
        conn.execute(
            tag_hierarchy_table.insert().values(
                parent_tag_id=row[1],
                child_tag_id=row[0],
                relationship_type='parent_child'
            )
        )
    
    # Remove the parent_tag_id column from the tags table
    op.drop_column('tags', 'parent_tag_id')


def downgrade():
    # Add back the parent_tag_id column to tags table
    op.add_column('tags', sa.Column('parent_tag_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key constraint back
    op.create_foreign_key(
        'tags_parent_tag_id_fkey', 
        'tags', 'tags', 
        ['parent_tag_id'], ['id']
    )
    
    # Migrate data back from tag_hierarchy to parent_tag_id
    # Define tables for the data migration
    tags_table = table(
        'tags',
        column('id', postgresql.UUID(as_uuid=True)),
        column('parent_tag_id', postgresql.UUID(as_uuid=True))
    )
    
    tag_hierarchy_table = table(
        'tag_hierarchy',
        column('parent_tag_id', postgresql.UUID(as_uuid=True)),
        column('child_tag_id', postgresql.UUID(as_uuid=True))
    )
    
    # Update parent_tag_id for each child tag (only one parent per child in downgrade)
    conn = op.get_bind()
    results = conn.execute(
        sa.select([tag_hierarchy_table.c.parent_tag_id, tag_hierarchy_table.c.child_tag_id])
    )
    
    # Group by child_tag_id to avoid multiple parents
    child_to_parent = {}
    for parent_id, child_id in results:
        if child_id not in child_to_parent:
            child_to_parent[child_id] = parent_id
    
    # Update each child tag with its first parent
    for child_id, parent_id in child_to_parent.items():
        conn.execute(
            tags_table.update().
            where(tags_table.c.id == child_id).
            values(parent_tag_id=parent_id)
        )
    
    # Drop indexes for tag_normalizations
    op.drop_index(op.f('ix_tag_normalizations_status_source'), table_name='tag_normalizations')
    op.drop_index(op.f('ix_tag_normalizations_approved_tag_id'), table_name='tag_normalizations')
    op.drop_index(op.f('ix_tag_normalizations_source'), table_name='tag_normalizations')
    op.drop_index(op.f('ix_tag_normalizations_review_status'), table_name='tag_normalizations')
    op.drop_index(op.f('ix_tag_normalizations_normalized_name'), table_name='tag_normalizations')
    op.drop_index(op.f('ix_tag_normalizations_original_name'), table_name='tag_normalizations')
    
    # Drop the tag_normalizations table
    op.drop_table('tag_normalizations')
    
    # Drop the indexes first
    op.drop_index('ix_tag_hierarchy_full', table_name='tag_hierarchy')
    op.drop_index('ix_tag_hierarchy_rel_type', table_name='tag_hierarchy')
    op.drop_index('ix_tag_hierarchy_child_tag_id', table_name='tag_hierarchy')
    op.drop_index('ix_tag_hierarchy_parent_tag_id', table_name='tag_hierarchy')
    
    # Then drop the tag_hierarchy table
    op.drop_table('tag_hierarchy')
    
    # Drop the enums
    conn = op.get_bind()
    conn.execute(sa.text("DROP TYPE IF EXISTS tag_review_status CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS tag_source CASCADE"))
