"""mission_15_agency

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agency tables for Mission 15."""
    # --- AgencyAccount ---
    op.create_table('agencyaccount',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('owner_user_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', name='agencystatus'), nullable=False),
        sa.Column('plan_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['owner_user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_agencyaccount_id'), 'agencyaccount', ['id'])
    op.create_index(op.f('ix_agencyaccount_name'), 'agencyaccount', ['name'])
    op.create_index(op.f('ix_agencyaccount_owner_user_id'), 'agencyaccount', ['owner_user_id'])

    # --- AgencyMember ---
    op.create_table('agencymember',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('agency_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.Enum('AGENCY_OWNER', 'AGENCY_ADMIN', 'AGENCY_OPERATOR', 'AGENCY_VIEWER', name='agencyrole'), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencyaccount.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'user_id'),
    )
    op.create_index(op.f('ix_agencymember_id'), 'agencymember', ['id'])
    op.create_index(op.f('ix_agencymember_agency_id'), 'agencymember', ['agency_id'])
    op.create_index(op.f('ix_agencymember_user_id'), 'agencymember', ['user_id'])

    # --- WorkspaceOwnership ---
    op.create_table('workspaceownership',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('owner_type', sa.Enum('USER', 'AGENCY', name='ownertype'), nullable=False),
        sa.Column('owner_user_id', sa.Uuid(), nullable=True),
        sa.Column('owner_agency_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id']),
        sa.ForeignKeyConstraint(['owner_user_id'], ['user.id']),
        sa.ForeignKeyConstraint(['owner_agency_id'], ['agencyaccount.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_workspaceownership_id'), 'workspaceownership', ['id'])
    op.create_index(op.f('ix_workspaceownership_workspace_id'), 'workspaceownership', ['workspace_id'], unique=True)
    op.create_index(op.f('ix_workspaceownership_owner_agency_id'), 'workspaceownership', ['owner_agency_id'])

    # --- Backfill: create WorkspaceOwnership for existing workspaces ---
    # Assign each existing workspace to its first OWNER member
    op.execute("""
        INSERT INTO workspaceownership (id, created_at, updated_at, workspace_id, owner_type, owner_user_id, owner_agency_id)
        SELECT
            lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))),
            datetime('now'),
            datetime('now'),
            wm.workspace_id,
            'USER',
            wm.user_id,
            NULL
        FROM workspacemember wm
        WHERE wm.role = 'owner'
        AND wm.workspace_id NOT IN (SELECT workspace_id FROM workspaceownership)
        GROUP BY wm.workspace_id
    """)


def downgrade() -> None:
    """Drop agency tables."""
    op.drop_table('workspaceownership')
    op.drop_table('agencymember')
    op.drop_table('agencyaccount')
