"""02_create_tags_table

Revision ID: 02_create_tags
Revises: 01_create_users
Create Date: 2025-05-03 12:54:37.622765

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '02_create_tags'
down_revision = '01_create_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tags table with parent-child relationship
    op.create_table(
        'tags',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('tag_type', sa.Enum('language', 'framework', 'concept', 'domain', 'skill_level', 'tool', 'topic', name='tagtype'),
                  server_default='concept', nullable=True),
        sa.Column('is_featured', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_private', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('parent_tag_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['parent_tag_id'], ['tags.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # Create index on name for lookup and ensure uniqueness
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=True)
    
    # Create user_tags association table
    op.create_table(
        'user_tags',
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('user_tags')
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_table('tags')
    
    # Drop the tag_type enum explicitly
    op.execute('DROP TYPE IF EXISTS tagtype;')
