"""Remove mirror_name and change build_version to string

Revision ID: f1a2b3c4d5e6
Revises: 81d6080bfa9c
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '81d6080bfa9c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove mirror_name column from user_projects
    op.drop_column('user_projects', 'mirror_name')
    
    # Change build_version from Integer to String for semantic versioning (1.0, 1.1, etc.)
    op.alter_column(
        'project_builds',
        'build_version',
        type_=sa.String(),
        postgresql_using='build_version::text',
        existing_nullable=False
    )


def downgrade() -> None:
    # Re-add mirror_name column
    op.add_column('user_projects', sa.Column('mirror_name', sa.String(), nullable=True))
    
    # Revert build_version back to Integer
    op.alter_column(
        'project_builds',
        'build_version',
        type_=sa.Integer(),
        postgresql_using='build_version::integer',
        existing_nullable=False
    )
