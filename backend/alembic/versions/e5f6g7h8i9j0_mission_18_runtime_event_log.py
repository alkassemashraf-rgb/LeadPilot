"""Mission 18 — Runtime Event Log

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f6g7h8i9j0"
down_revision = "d4e5f6g7h8i9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtimeeventlog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("related_ids", sa.JSON(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runtimeeventlog_workspace_id", "runtimeeventlog", ["workspace_id"])
    op.create_index("ix_runtimeeventlog_event_type", "runtimeeventlog", ["event_type"])
    op.create_index("ix_runtimeeventlog_source", "runtimeeventlog", ["source"])
    op.create_index("ix_runtimeeventlog_correlation_id", "runtimeeventlog", ["correlation_id"])
    op.create_index("ix_runtimeeventlog_created_at", "runtimeeventlog", ["created_at"])
    op.create_index("idx_rte_ws_created", "runtimeeventlog", ["workspace_id", "created_at"])
    op.create_index("idx_rte_correlation", "runtimeeventlog", ["correlation_id"])
    op.create_index("idx_rte_type_created", "runtimeeventlog", ["event_type", "created_at"])
    op.create_index("idx_rte_source_created", "runtimeeventlog", ["source", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_rte_source_created", table_name="runtimeeventlog")
    op.drop_index("idx_rte_type_created", table_name="runtimeeventlog")
    op.drop_index("idx_rte_correlation", table_name="runtimeeventlog")
    op.drop_index("idx_rte_ws_created", table_name="runtimeeventlog")
    op.drop_index("ix_runtimeeventlog_created_at", table_name="runtimeeventlog")
    op.drop_index("ix_runtimeeventlog_correlation_id", table_name="runtimeeventlog")
    op.drop_index("ix_runtimeeventlog_source", table_name="runtimeeventlog")
    op.drop_index("ix_runtimeeventlog_event_type", table_name="runtimeeventlog")
    op.drop_index("ix_runtimeeventlog_workspace_id", table_name="runtimeeventlog")
    op.drop_table("runtimeeventlog")
