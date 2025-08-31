"""
Add daily challenge tracking fields to User model

Revision ID: 11_add_challenge_tracking_users
Revises: custom_add_password_reset_tokens
Create Date: 2025-05-20

This migration adds several new fields to the users table to support daily challenge email functionality:
- last_problem_sent_id: Tracks the ID of the last problem sent to the user
- last_problem_sent_at: Tracks when the last problem was sent
- is_premium: Indicates whether the user has premium status (for future premium features)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic
revision = '11_add_challenge_tracking_users'
down_revision = 'custom_add_password_reset_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to users table
    op.add_column('users', sa.Column('last_problem_sent_id', UUID(as_uuid=True), sa.ForeignKey("problems.id"), nullable=True))
    op.add_column('users', sa.Column('last_problem_sent_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('is_premium', sa.Boolean(), server_default='false', nullable=False))
    
    # Create an index on last_problem_sent_at for more efficient queries
    # This will help with finding users who need solutions sent after 24 hours
    op.create_index('ix_users_last_problem_sent_at', 'users', ['last_problem_sent_at'])


def downgrade() -> None:
    # Remove the index first, then the columns
    op.drop_index('ix_users_last_problem_sent_at', table_name='users')
    op.drop_column('users', 'is_premium')
    op.drop_column('users', 'last_problem_sent_at')
    op.drop_column('users', 'last_problem_sent_id')
