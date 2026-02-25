"""add unique constraint to zoho_lead_mapping workspace_id

Revision ID: 5c3fecea0533
Revises: 4b1048284463
Create Date: 2026-02-19 15:46:56.129449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c3fecea0533'
down_revision: Union[str, Sequence[str], None] = '4b1048284463'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("zoholeadmapping") as batch_op:
        batch_op.create_unique_constraint("uq_zoho_lead_mapping_workspace", ["workspace_id"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("zoholeadmapping") as batch_op:
        batch_op.drop_constraint("uq_zoho_lead_mapping_workspace", type_="unique")
