"""mission_7_inbox_foundation

Revision ID: 602899cf266d
Revises: 50ef7c49247d
Create Date: 2026-02-19 14:36:03.165464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '602899cf266d'
down_revision: Union[str, Sequence[str], None] = '50ef7c49247d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    try:
        with op.batch_alter_table('contact', schema=None) as batch_op:
            batch_op.add_column(sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    except Exception:
        pass

    try:
        with op.batch_alter_table('conversation', schema=None) as batch_op:
            batch_op.add_column(sa.Column('status', sa.Enum('BOT_ACTIVE', 'HUMAN_TAKEOVER', 'CLOSED', name='conversationstatus'), nullable=False, server_default='bot_active'))
            batch_op.create_index('idx_conv_workspace_contact', ['workspace_id', 'contact_id'], unique=False)
            batch_op.create_index('idx_conv_workspace_updated', ['workspace_id', 'updated_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_conversation_status'), ['status'], unique=False)
    except Exception:
        pass

    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.create_index('idx_msg_conv_created', ['conversation_id', 'created_at'], unique=False)
    except Exception:
        pass

def downgrade() -> None:
    """Downgrade schema."""
    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.drop_index('idx_msg_conv_created')
    except Exception:
        pass

    try:
        with op.batch_alter_table('conversation', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_conversation_status'))
            batch_op.drop_index('idx_conv_workspace_updated')
            batch_op.drop_index('idx_conv_workspace_contact')
            batch_op.drop_column('status')
    except Exception:
        pass

    try:
        with op.batch_alter_table('contact', schema=None) as batch_op:
            batch_op.drop_column('display_name')
    except Exception:
        pass
