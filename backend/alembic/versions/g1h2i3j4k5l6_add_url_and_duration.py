"""Add project_access_url and duration columns

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-02-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_access_url to user_projects
    op.add_column('user_projects', sa.Column('project_access_url', sa.String(), nullable=True))
    
    # Add duration (in seconds) to project_builds
    op.add_column('project_builds', sa.Column('duration', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_projects', 'project_access_url')
    op.drop_column('project_builds', 'duration')
