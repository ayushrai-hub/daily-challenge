"""06b_enhance_problem_model

Revision ID: 06b_enhance_problem_model
Revises: 06a_enhance_tag_model
Create Date: 2025-05-03 18:26:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision = '06b_enhance_problem_model'
down_revision = '06a_enhance_tag_model'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Skip DifficultyLevel enum and difficulty column operations
    # The enum and column are already created in 04_create_problems_table.py
    
    # Check if the difficultylevel enum exists before creating it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_enums = inspector.get_enums()
    
    # Only create the enum if it doesn't exist
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'difficultylevel':
            enum_exists = True
            break
    
    if not enum_exists:
        difficultylevel = ENUM('easy', 'medium', 'hard',
                              name='difficultylevel', create_type=True)
        difficultylevel.create(op.get_bind(), checkfirst=True)
        
    # Skip the data migration and column drop operations since
    # our base migrations already use the enum directly
    
    # Skip ProblemStatus enum creation and migration
    # These operations are already handled in 04_create_problems_table.py
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_enums = inspector.get_enums()
    
    # Check for problemstatus enum
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'problemstatus':
            enum_exists = True
            break
    
    if not enum_exists:
        problemstatus = ENUM('draft', 'approved', 'archived', 'pending',
                           name='problemstatus', create_type=True)
        problemstatus.create(op.get_bind(), checkfirst=True)
    
    # Check if we have a status column with the right type
    inspector = sa.inspect(conn)
    status_columns = [col for col in inspector.get_columns('problems') if col['name'] == 'status']
    
    # Skip all status column operations since they're already in the base migrations
    
    # Skip VettingTier enum changes as they're already in the base migrations
    enum_exists = False
    for enum in existing_enums:
        if enum['name'] == 'vettingtier':
            enum_exists = True
            break
    
    if not enum_exists:
        vettingtier = ENUM('tier1', 'tier2', 'tier3',
                          name='vettingtier', create_type=True)
        vettingtier.create(op.get_bind(), checkfirst=True)
    
    # Add approved_at column
    op.add_column('problems', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))
    
    # Update approved_at for problems that are already approved
    op.execute("""
        UPDATE problems
        SET approved_at = updated_at
        WHERE status = 'approved'
    """)


def downgrade() -> None:
    # Only remove approved_at column since that was all we actually added in the upgrade method
    op.drop_column('problems', 'approved_at')
    
    # Skip all the enum operations since we're not changing the enums in the upgrade method anymore
    pass
