"""mission_ma_adk_step_log

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-03-24 00:00:00.000000

Make ExecutionStepLog.node_id nullable so ADK tool-call logs can be
written without a FlowNode FK (ADK tool calls have no node IDs).
"""
from alembic import op
import sqlalchemy as sa

revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("executionsteplog") as batch_op:
        batch_op.alter_column(
            "node_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )


def downgrade():
    with op.batch_alter_table("executionsteplog") as batch_op:
        batch_op.alter_column(
            "node_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )
