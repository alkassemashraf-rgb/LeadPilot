"""Mission M-D: flow builder revamp — add adk_pipeline_config to flowversion,
add resume_at + resume_node_id to executioninstance

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- flowversion: add adk_pipeline_config ---
    fv_cols = {c["name"] for c in inspector.get_columns("flowversion")}
    if "adk_pipeline_config" not in fv_cols:
        op.add_column(
            "flowversion",
            sa.Column("adk_pipeline_config", sa.JSON(), nullable=True),
        )

    # --- executioninstance: add resume_at + resume_node_id ---
    ei_cols = {c["name"] for c in inspector.get_columns("executioninstance")}
    if "resume_at" not in ei_cols:
        op.add_column(
            "executioninstance",
            sa.Column("resume_at", sa.DateTime(), nullable=True),
        )
    if "resume_node_id" not in ei_cols:
        op.add_column(
            "executioninstance",
            sa.Column("resume_node_id", sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("executioninstance", "resume_node_id")
    op.drop_column("executioninstance", "resume_at")
    op.drop_column("flowversion", "adk_pipeline_config")
