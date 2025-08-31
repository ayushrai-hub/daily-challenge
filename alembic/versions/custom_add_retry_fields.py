"""Add retry fields to email_queue table

Revision ID: custom_add_retry_fields
Revises: 07b3e1e4c8d2
Create Date: 2025-05-08 12:42:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'custom_add_retry_fields'
down_revision = '07b3e1e4c8d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add retry-related columns to the email_queue table"""
    # Add retry tracking fields
    op.add_column('email_queue', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('email_queue', sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('email_queue', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('email_queue', sa.Column('delivery_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove the retry-related columns from email_queue table"""
    op.drop_column('email_queue', 'delivery_data')
    op.drop_column('email_queue', 'max_retries')
    op.drop_column('email_queue', 'last_retry_at')
    op.drop_column('email_queue', 'retry_count')
