"""Create email_queue table\n\nRevision ID: 07b_create_email_queue_table\nRevises: 07a_add_is_email_verified_and_clean_email_queue\nCreate Date: 2025-05-07 15:44:00\n\n"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '07b3e1e4c8d2'
down_revision = '07aaddb2f1c3'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'email_queue',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False, primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('email_type', sa.String(), nullable=False, index=True),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('html_content', sa.Text(), nullable=False),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('template_id', sa.String(), nullable=True),
        sa.Column('template_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'cancelled', name='emailstatus'), nullable=False, server_default='pending', index=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('tracking_id', sa.String(), nullable=True),
        sa.Column('problem_id', UUID(as_uuid=True), sa.ForeignKey('problems.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

def downgrade():
    op.drop_table('email_queue')
    # Drop the ENUM type for status
    op.execute('DROP TYPE IF EXISTS emailstatus;')
