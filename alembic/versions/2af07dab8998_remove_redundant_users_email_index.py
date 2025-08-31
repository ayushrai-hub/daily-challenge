"""remove_redundant_users_email_index

Revision ID: 2af07dab8998
Revises: 05_create_delivery_logs
Create Date: 2025-05-03 13:43:43.304294

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2af07dab8998'
down_revision = '05_create_delivery_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The unique constraint 'users_email_key' already ensures uniqueness
    # Drop the redundant ix_users_email index
    op.drop_index('ix_users_email', table_name='users')


def downgrade() -> None:
    # Recreate the index if we need to downgrade
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
