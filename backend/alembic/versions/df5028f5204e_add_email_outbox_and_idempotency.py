"""add_email_outbox_and_idempotency

Revision ID: df5028f5204e
Revises: 037083c922cb
Create Date: 2026-02-20 13:14:38.517026

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'df5028f5204e'
down_revision: Union[str, Sequence[str], None] = '037083c922cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- systemmoduleconfig ---
    try:
        op.create_table('systemmoduleconfig',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('module_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_systemmoduleconfig_id'), 'systemmoduleconfig', ['id'], unique=False)
        op.create_index(op.f('ix_systemmoduleconfig_module_name'), 'systemmoduleconfig', ['module_name'], unique=True)
    except Exception:
        pass

    # --- emaillog ---
    try:
        op.create_table('emaillog',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('workspace_id', sa.Uuid(), nullable=True),
            sa.Column('user_id', sa.Uuid(), nullable=True),
            sa.Column('email_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('recipient', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('subject', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('status', sa.Enum('PENDING', 'SENT', 'FAILED', name='emailstatus'), nullable=False),
            sa.Column('attempt_count', sa.Integer(), nullable=False),
            sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('provider_message_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('idempotency_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('sent_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_emaillog_st_created', 'emaillog', ['status', 'created_at'], unique=False)
        op.create_index('idx_emaillog_w_created', 'emaillog', ['workspace_id', 'created_at'], unique=False)
        op.create_index(op.f('ix_emaillog_email_type'), 'emaillog', ['email_type'], unique=False)
        op.create_index(op.f('ix_emaillog_id'), 'emaillog', ['id'], unique=False)
        op.create_index(op.f('ix_emaillog_idempotency_key'), 'emaillog', ['idempotency_key'], unique=True)
        op.create_index(op.f('ix_emaillog_recipient'), 'emaillog', ['recipient'], unique=False)
        op.create_index(op.f('ix_emaillog_status'), 'emaillog', ['status'], unique=False)
        op.create_index(op.f('ix_emaillog_user_id'), 'emaillog', ['user_id'], unique=False)
        op.create_index(op.f('ix_emaillog_workspace_id'), 'emaillog', ['workspace_id'], unique=False)
    except Exception:
        pass

    # --- emailoutbox ---
    try:
        op.create_table('emailoutbox',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('email_log_id', sa.Uuid(), nullable=False),
            sa.Column('email_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('payload_json', sa.JSON(), nullable=True),
            sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'SENT', 'FAILED', name='emailoutboxstatus'), nullable=False),
            sa.Column('attempt_count', sa.Integer(), nullable=False),
            sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
            sa.Column('locked_at', sa.DateTime(), nullable=True),
            sa.Column('last_error', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.ForeignKeyConstraint(['email_log_id'], ['emaillog.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_emailoutbox_email_log_id'), 'emailoutbox', ['email_log_id'], unique=True)
        op.create_index(op.f('ix_emailoutbox_email_type'), 'emailoutbox', ['email_type'], unique=False)
        op.create_index(op.f('ix_emailoutbox_id'), 'emailoutbox', ['id'], unique=False)
        op.create_index(op.f('ix_emailoutbox_next_attempt_at'), 'emailoutbox', ['next_attempt_at'], unique=False)
        op.create_index(op.f('ix_emailoutbox_status'), 'emailoutbox', ['status'], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index(op.f('ix_emailoutbox_status'), table_name='emailoutbox')
        op.drop_index(op.f('ix_emailoutbox_next_attempt_at'), table_name='emailoutbox')
        op.drop_index(op.f('ix_emailoutbox_id'), table_name='emailoutbox')
        op.drop_index(op.f('ix_emailoutbox_email_type'), table_name='emailoutbox')
        op.drop_index(op.f('ix_emailoutbox_email_log_id'), table_name='emailoutbox')
        op.drop_table('emailoutbox')
    except Exception:
        pass
    
    try:
        op.drop_index(op.f('ix_emaillog_workspace_id'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_user_id'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_status'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_recipient'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_idempotency_key'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_id'), table_name='emaillog')
        op.drop_index(op.f('ix_emaillog_email_type'), table_name='emaillog')
        op.drop_index('idx_emaillog_w_created', table_name='emaillog')
        op.drop_index('idx_emaillog_st_created', table_name='emaillog')
        op.drop_table('emaillog')
    except Exception:
        pass

    try:
        op.drop_index(op.f('ix_systemmoduleconfig_module_name'), table_name='systemmoduleconfig')
        op.drop_index(op.f('ix_systemmoduleconfig_id'), table_name='systemmoduleconfig')
        op.drop_table('systemmoduleconfig')
    except Exception:
        pass
    # ### end Alembic commands ###
