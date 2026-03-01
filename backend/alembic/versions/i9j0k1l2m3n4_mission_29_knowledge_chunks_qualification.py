"""Mission 29 — Knowledge chunks + qualification criteria tables

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

revision = "i9j0k1l2m3n4"
down_revision = "h8i9j0k1l2m3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- KnowledgeChunk ---
    op.create_table(
        "knowledgechunk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_file_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["knowledge_file_id"], ["workspaceknowledgefile.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledgechunk_workspace_id", "knowledgechunk", ["workspace_id"])
    op.create_index("ix_knowledgechunk_knowledge_file_id", "knowledgechunk", ["knowledge_file_id"])
    op.create_index("idx_kc_ws_file", "knowledgechunk", ["workspace_id", "knowledge_file_id"])

    # --- QualificationCriterion ---
    op.create_table(
        "qualificationcriterion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("criterion_type", sa.String(), nullable=False, server_default="boolean"),
        sa.Column("enum_values", sa.JSON(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "code", name="uq_qualcriterion_ws_code"),
    )
    op.create_index("ix_qualificationcriterion_workspace_id", "qualificationcriterion", ["workspace_id"])
    op.create_index("ix_qualificationcriterion_code", "qualificationcriterion", ["code"])


def downgrade() -> None:
    op.drop_table("qualificationcriterion")
    op.drop_table("knowledgechunk")
