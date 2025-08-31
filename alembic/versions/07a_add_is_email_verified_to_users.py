"""Add is_email_verified to users

Revision ID: 07aaddb2f1c3
Revises: 06d_enhance_delivery_log_model
Create Date: 2025-05-07 15:29:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '07aaddb2f1c3'
down_revision = '06d_enhance_delivery_log_model'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Add is_email_verified column to users (default False)
    op.add_column('users',
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false'))
    )

    # 2. Mark all active users as verified
    op.execute("UPDATE users SET is_email_verified = true WHERE is_active = true")

def downgrade():
    # 1. Remove is_email_verified column
    op.drop_column('users', 'is_email_verified')

    # 2. (Optional) Re-add 'id' column to email_queue
    with op.batch_alter_table('email_queue') as batch_op:
        batch_op.add_column(sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True))
