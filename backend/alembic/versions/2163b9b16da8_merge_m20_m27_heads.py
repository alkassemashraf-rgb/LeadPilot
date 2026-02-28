"""merge_m20_m27_heads

Revision ID: 2163b9b16da8
Revises: f6g7h8i9j0k1, g7h8i9j0k1l2
Create Date: 2026-02-28 09:08:59.083592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2163b9b16da8'
down_revision: Union[str, Sequence[str], None] = ('f6g7h8i9j0k1', 'g7h8i9j0k1l2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
