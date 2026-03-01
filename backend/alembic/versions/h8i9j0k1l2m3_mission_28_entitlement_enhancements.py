"""mission_28_entitlement_enhancements

Revision ID: h8i9j0k1l2m3
Revises: 2163b9b16da8
Create Date: 2026-02-28 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "2163b9b16da8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'enabled' column to WorkspaceEntitlementOverride
    # Nullable bool: None = inherit from plan, True = force-enable, False = force-disable
    op.add_column(
        "workspaceentitlementoverride",
        sa.Column("enabled", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaceentitlementoverride", "enabled")
