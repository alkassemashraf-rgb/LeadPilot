"""Mission 20 — Knowledge Files Enhancement + Qualification Config

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6g7h8i9j0k1"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Knowledge file enhancements ---
    op.add_column(
        "workspaceknowledgefile",
        sa.Column("sha256_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "workspaceknowledgefile",
        sa.Column("status", sa.String(), nullable=False, server_default="READY"),
    )
    op.create_index(
        "ix_wkf_sha256",
        "workspaceknowledgefile",
        ["sha256_hash"],
    )

    # --- Qualification config table ---
    op.create_table(
        "qualificationconfig",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("qualification_questions", sa.JSON(), nullable=True),
        sa.Column("qualification_statuses", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
    )
    op.create_index(
        "ix_qualificationconfig_workspace_id",
        "qualificationconfig",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_table("qualificationconfig")
    op.drop_index("ix_wkf_sha256", table_name="workspaceknowledgefile")
    op.drop_column("workspaceknowledgefile", "status")
    op.drop_column("workspaceknowledgefile", "sha256_hash")
