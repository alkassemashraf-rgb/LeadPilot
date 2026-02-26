"""mission_14_entitlements

Revision ID: a1b2c3d4e5f6
Revises: d820eb9ff19c
Create Date: 2026-02-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd820eb9ff19c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create entitlement tables for Mission 14."""
    # --- Plan ---
    op.create_table('plan',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('display_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_plan_id'), 'plan', ['id'], unique=False)
    op.create_index(op.f('ix_plan_name'), 'plan', ['name'], unique=True)

    # --- PlanEntitlement ---
    op.create_table('planentitlement',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('module_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('hard_limit', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_id', 'module_key')
    )
    op.create_index(op.f('ix_planentitlement_id'), 'planentitlement', ['id'], unique=False)
    op.create_index(op.f('ix_planentitlement_plan_id'), 'planentitlement', ['plan_id'], unique=False)
    op.create_index(op.f('ix_planentitlement_module_key'), 'planentitlement', ['module_key'], unique=False)

    # --- WorkspacePlan ---
    op.create_table('workspaceplan',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('plan_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_by', sa.Uuid(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assigned_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['plan.id'], ),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaceplan_id'), 'workspaceplan', ['id'], unique=False)
    op.create_index(op.f('ix_workspaceplan_workspace_id'), 'workspaceplan', ['workspace_id'], unique=True)
    op.create_index(op.f('ix_workspaceplan_plan_id'), 'workspaceplan', ['plan_id'], unique=False)

    # --- WorkspaceEntitlementOverride ---
    op.create_table('workspaceentitlementoverride',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('module_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('hard_limit', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'module_key')
    )
    op.create_index(op.f('ix_workspaceentitlementoverride_id'), 'workspaceentitlementoverride', ['id'], unique=False)
    op.create_index(op.f('ix_workspaceentitlementoverride_workspace_id'), 'workspaceentitlementoverride', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_workspaceentitlementoverride_module_key'), 'workspaceentitlementoverride', ['module_key'], unique=False)

    # --- UsageMeter ---
    op.create_table('usagemeter',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('module_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('period', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('counter', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'module_key', 'period')
    )
    op.create_index(op.f('ix_usagemeter_workspace_id'), 'usagemeter', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_usagemeter_module_key'), 'usagemeter', ['module_key'], unique=False)
    op.create_index(op.f('ix_usagemeter_period'), 'usagemeter', ['period'], unique=False)


def downgrade() -> None:
    """Drop entitlement tables."""
    op.drop_index(op.f('ix_usagemeter_period'), table_name='usagemeter')
    op.drop_index(op.f('ix_usagemeter_module_key'), table_name='usagemeter')
    op.drop_index(op.f('ix_usagemeter_workspace_id'), table_name='usagemeter')
    op.drop_table('usagemeter')

    op.drop_index(op.f('ix_workspaceentitlementoverride_module_key'), table_name='workspaceentitlementoverride')
    op.drop_index(op.f('ix_workspaceentitlementoverride_workspace_id'), table_name='workspaceentitlementoverride')
    op.drop_index(op.f('ix_workspaceentitlementoverride_id'), table_name='workspaceentitlementoverride')
    op.drop_table('workspaceentitlementoverride')

    op.drop_index(op.f('ix_workspaceplan_plan_id'), table_name='workspaceplan')
    op.drop_index(op.f('ix_workspaceplan_workspace_id'), table_name='workspaceplan')
    op.drop_index(op.f('ix_workspaceplan_id'), table_name='workspaceplan')
    op.drop_table('workspaceplan')

    op.drop_index(op.f('ix_planentitlement_module_key'), table_name='planentitlement')
    op.drop_index(op.f('ix_planentitlement_plan_id'), table_name='planentitlement')
    op.drop_index(op.f('ix_planentitlement_id'), table_name='planentitlement')
    op.drop_table('planentitlement')

    op.drop_index(op.f('ix_plan_name'), table_name='plan')
    op.drop_index(op.f('ix_plan_id'), table_name='plan')
    op.drop_table('plan')
