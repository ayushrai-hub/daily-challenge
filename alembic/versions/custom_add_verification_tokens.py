"""
Add verification tokens table for email verification

Revision ID: custom_add_verification_tokens
Revises: custom_add_retry_fields
Create Date: 2025-05-08 14:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'custom_add_verification_tokens'
down_revision = 'custom_add_retry_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the verification_tokens table."""
    op.create_table(
        'verification_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('token_type', sa.String(), nullable=False, server_default='email_verification'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_verification_tokens_token'), 'verification_tokens', ['token'], unique=False)


def downgrade() -> None:
    """Drop the verification_tokens table."""
    op.drop_index(op.f('ix_verification_tokens_token'), table_name='verification_tokens')
    op.drop_table('verification_tokens')
