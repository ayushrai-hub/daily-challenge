"""06d_enhance_delivery_log_model

Revision ID: 06d_enhance_delivery_log_model
Revises: 06c_enhance_content_source_model
Create Date: 2025-05-03 18:41:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '06d_enhance_delivery_log_model'
down_revision = '06c_enhance_content_source_model'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check for existing enums
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_enums = inspector.get_enums()
    existing_columns = [col['name'] for col in inspector.get_columns('delivery_logs')]
    
    # Skip enum creation if it already exists
    deliverychannel_exists = False
    for enum in existing_enums:
        if enum['name'] == 'deliverychannel':
            deliverychannel_exists = True
            break
    
    if not deliverychannel_exists:
        deliverychannel = ENUM('email', 'sms', 'push', 'in_app',
                             name='deliverychannel', create_type=True)
        deliverychannel.create(op.get_bind(), checkfirst=True)
    
    # Skip delivery_channel column creation - already in base migration
    
    # Skip DeliveryStatus enum creation if it already exists
    deliverystatus_exists = False
    for enum in existing_enums:
        if enum['name'] == 'deliverystatus':
            deliverystatus_exists = True
            break
    
    if not deliverystatus_exists:
        deliverystatus = ENUM('pending', 'scheduled', 'delivered', 'opened', 'completed', 'failed',
                            name='deliverystatus', create_type=True)
        deliverystatus.create(op.get_bind(), checkfirst=True)
    
    # Skip status column operations - already handled in base migration
    
    # Add additional timestamp columns only if they don't exist
    if 'scheduled_at' not in existing_columns:
        op.add_column('delivery_logs', sa.Column('scheduled_at', sa.DateTime(timezone=True), 
                                              server_default=sa.func.now(), nullable=False))
    
    if 'opened_at' not in existing_columns:
        op.add_column('delivery_logs', sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'completed_at' not in existing_columns:
        op.add_column('delivery_logs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Change delivered_at to be nullable (it will be NULL until actually delivered) if it exists
    if 'delivered_at' in existing_columns:
        op.alter_column('delivery_logs', 'delivered_at', nullable=True, server_default=None)
    
    # Rename 'metadata' column to 'meta' for consistency with model if it exists
    if 'metadata' in existing_columns and 'meta' not in existing_columns:
        op.alter_column('delivery_logs', 'metadata', new_column_name='meta')


def downgrade() -> None:
    # Check which columns exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('delivery_logs')]
    
    # Only revert columns we added or modified in the upgrade method
    
    # Rename 'meta' back to 'metadata' if it exists
    if 'meta' in existing_columns and 'metadata' not in existing_columns:
        op.alter_column('delivery_logs', 'meta', new_column_name='metadata')
    
    # Revert delivered_at column to non-nullable with default if it exists
    if 'delivered_at' in existing_columns:
        op.alter_column('delivery_logs', 'delivered_at', nullable=False, 
                        server_default=sa.func.now())
    
    # Drop additional timestamp columns if they exist
    if 'completed_at' in existing_columns:
        op.drop_column('delivery_logs', 'completed_at')
    
    if 'opened_at' in existing_columns:
        op.drop_column('delivery_logs', 'opened_at')
    
    if 'scheduled_at' in existing_columns:
        op.drop_column('delivery_logs', 'scheduled_at')
    
    # Skip the enum drops since they're handled elsewhere
    # We don't want to drop enums that might still be in use by other tables
