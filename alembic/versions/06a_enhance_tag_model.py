"""06a_enhance_tag_model

Revision ID: 06a_enhance_tag_model
Revises: 2af07dab8998
Create Date: 2025-05-03 18:18:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '06a_enhance_tag_model'
down_revision = '2af07dab8998'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip these operations since they're now included in the base migration
    # The columns tag_type, is_featured, and is_private are already added in 02_create_tags_table.py
    
    # Check if the tag_type enum exists before creating it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_enums = inspector.get_enums()
    
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'tagtype':
            enum_exists = True
            break
    
    # Only create the enum if it doesn't exist
    if not enum_exists:
        tagtype = ENUM('language', 'framework', 'concept', 'domain', 'skill_level', 'tool', 'topic',
                      name='tagtype', create_type=True)
        tagtype.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # Drop added columns
    op.drop_column('tags', 'is_private')
    op.drop_column('tags', 'is_featured')
    op.drop_column('tags', 'tag_type')
    
    # Drop TagType enum using PostgreSQL-specific approach
    tagtype = ENUM(name='tagtype')
    tagtype.drop(op.get_bind())
