"""merge heads

Revision ID: 81d6080bfa9c
Revises: a1b2c3d4e5f6, b1c2d3e4f5g6
Create Date: 2026-02-07 06:56:13.290665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81d6080bfa9c'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'b1c2d3e4f5g6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
