"""Add webhook_id to user_projects table

Revision ID: b1c2d3e4f5g6
Revises: 65e8346a7912
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = '65e8346a7912'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add webhook_id column to store the GitHub webhook ID for auto-sync
    op.add_column('user_projects', sa.Column('webhook_id', sa.BigInteger(), nullable=True))
    # Add webhook_secret column to store the secret for verifying webhook payloads
    op.add_column('user_projects', sa.Column('webhook_secret', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_projects', 'webhook_secret')
    op.drop_column('user_projects', 'webhook_id')
