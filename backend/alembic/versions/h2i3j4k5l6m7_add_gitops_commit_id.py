"""add gitops_commit_id to project_builds

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add gitops_commit_id column to project_builds table
    op.add_column('project_builds', sa.Column('gitops_commit_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_builds', 'gitops_commit_id')
