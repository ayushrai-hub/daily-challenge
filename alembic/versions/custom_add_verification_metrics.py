"""Add verification metrics table

Revision ID: custom_add_verification_metrics
Revises: custom_add_verification_tokens
Create Date: 2025-05-08 15:33:02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'custom_add_verification_metrics'
down_revision = 'custom_add_verification_tokens'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'verification_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('verification_requests_sent', sa.Integer(), nullable=False, default=0),
        sa.Column('verification_completed', sa.Integer(), nullable=False, default=0),
        sa.Column('verification_expired', sa.Integer(), nullable=False, default=0),
        sa.Column('resend_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('avg_verification_time', sa.Float(), nullable=True),
        sa.Column('median_verification_time', sa.Float(), nullable=True),
        sa.Column('min_verification_time', sa.Float(), nullable=True),
        sa.Column('max_verification_time', sa.Float(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_updated', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add index for date lookup
    op.create_index(op.f('ix_verification_metrics_date'), 'verification_metrics', ['date'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_verification_metrics_date'), table_name='verification_metrics')
    op.drop_table('verification_metrics')
