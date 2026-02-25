"""mission_6_2_hardening

Revision ID: 50ef7c49247d
Revises: 408346e0ab60
Create Date: 2026-02-19 14:26:28.538761

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '50ef7c49247d'
down_revision: Union[str, Sequence[str], None] = '408346e0ab60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.add_column(sa.Column('idempotency_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    except Exception:
        pass
    
    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.create_index('idx_msg_poll', ['workspace_id', 'delivery_status', 'created_at'], unique=False)
            batch_op.create_index('idx_msg_retry', ['delivery_status', 'last_attempt_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_message_idempotency_hash'), ['idempotency_hash'], unique=False)
            batch_op.create_unique_constraint('uq_message_provider_id', ['provider_message_id'])
    except Exception:
        pass

    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            # batch_op.drop_index('ix_message_idempotency_key') 
            batch_op.drop_column('idempotency_key')
    except Exception:
        pass

def downgrade() -> None:
    """Downgrade schema."""
    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.add_column(sa.Column('idempotency_key', sa.VARCHAR(), nullable=True))
            batch_op.create_index('ix_message_idempotency_key', ['idempotency_key'], unique=False)
    except Exception:
        pass
        
    try:
        with op.batch_alter_table('message', schema=None) as batch_op:
            batch_op.drop_constraint('uq_message_provider_id', type_='unique')
            batch_op.drop_index(batch_op.f('ix_message_idempotency_hash'))
            batch_op.drop_index('idx_msg_retry')
            batch_op.drop_index('idx_msg_poll')
            batch_op.drop_column('idempotency_hash')
    except Exception:
        pass
