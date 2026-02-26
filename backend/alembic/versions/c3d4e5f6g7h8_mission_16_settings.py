"""mission_16_settings

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-26 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create settings tables for Mission 16."""
    # --- WorkspaceSettings ---
    op.create_table('workspacesettings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('updated_by_user_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id']),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workspacesettings_id'), 'workspacesettings', ['id'])
    op.create_index(op.f('ix_workspacesettings_workspace_id'), 'workspacesettings', ['workspace_id'], unique=True)

    # --- AgencySettings ---
    op.create_table('agencysettings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('updated_by_user_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencyaccount.id']),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agencysettings_id'), 'agencysettings', ['id'])
    op.create_index(op.f('ix_agencysettings_agency_id'), 'agencysettings', ['agency_id'], unique=True)

    # --- SystemSettings ---
    op.create_table('systemsettings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('singleton_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('settings_json', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('updated_by_user_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_systemsettings_id'), 'systemsettings', ['id'])
    op.create_index(op.f('ix_systemsettings_singleton_key'), 'systemsettings', ['singleton_key'], unique=True)


def downgrade() -> None:
    """Drop settings tables."""
    op.drop_table('systemsettings')
    op.drop_table('agencysettings')
    op.drop_table('workspacesettings')
