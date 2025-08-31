"""01_create_users_table

Revision ID: 01_create_users
Revises: 
Create Date: 2025-05-03 12:52:04.947352

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '01_create_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table with authentication fields
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('subscription_status', sa.Enum('active', 'paused', 'unsubscribed', name='subscriptionstatus'), 
                  server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    # Create index on email (for login and search)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    # Create index on full_name for searching users by name
    op.create_index(op.f('ix_users_full_name'), 'users', ['full_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_full_name'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # Enum is automatically dropped with table
