"""05_create_delivery_logs_table

Revision ID: 05_create_delivery_logs
Revises: 04_create_problems
Create Date: 2025-05-03 13:04:53.424529

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision = '05_create_delivery_logs'
down_revision = '04_create_problems'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create delivery_logs table
    op.create_table(
        'delivery_logs',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('problem_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('scheduled', 'delivered', 'failed', 'opened', 'completed', name='deliverystatus'), 
                  server_default='scheduled', nullable=False),
        sa.Column('delivery_channel', sa.Enum('email', 'slack', 'api', name='deliverychannel'),
                  server_default='email', nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes
    # User index for filtering/joins - frequent user-based queries
    op.create_index(op.f('ix_delivery_logs_user_id'), 'delivery_logs', ['user_id'], unique=False)
    # Problem index for filtering/joins - needed for problem stats
    op.create_index(op.f('ix_delivery_logs_problem_id'), 'delivery_logs', ['problem_id'], unique=False)
    # Delivery status index for filtering - used for reporting
    op.create_index(op.f('ix_delivery_logs_status'), 'delivery_logs', ['status'], unique=False)
    # Delivery channel index for filtering
    op.create_index(op.f('ix_delivery_logs_delivery_channel'), 'delivery_logs', ['delivery_channel'], unique=False)
    # Delivered at index for time-based queries - common date range filters
    op.create_index(op.f('ix_delivery_logs_delivered_at'), 'delivery_logs', ['delivered_at'], unique=False)
    # Composite user+problem index for uniqueness/lookup
    op.create_index(op.f('ix_delivery_logs_user_problem'), 'delivery_logs', ['user_id', 'problem_id'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_delivery_logs_user_problem'), table_name='delivery_logs')
    op.drop_index(op.f('ix_delivery_logs_delivered_at'), table_name='delivery_logs')
    op.drop_index(op.f('ix_delivery_logs_status'), table_name='delivery_logs')
    op.drop_index(op.f('ix_delivery_logs_delivery_channel'), table_name='delivery_logs')
    op.drop_index(op.f('ix_delivery_logs_problem_id'), table_name='delivery_logs')
    op.drop_index(op.f('ix_delivery_logs_user_id'), table_name='delivery_logs')
    
    # Drop table
    op.drop_table('delivery_logs')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS deliverystatus;')
    op.execute('DROP TYPE IF EXISTS deliverychannel;')
