"""mission_38_social_login

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-03-21 00:00:00.000000

Creates user_identity table for social login (Facebook, TikTok).
Adds purpose column to oauthstate for flow disambiguation.
"""
from alembic import op
import sqlalchemy as sa

revision = "o5p6q7r8s9t0"
down_revision = "n4o5p6q7r8s9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # --- user_identity table (idempotent: create_all may have already created it) ---
    if "user_identity" not in existing_tables:
        op.create_table(
            "user_identity",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("provider_code", sa.String(), nullable=False),
            sa.Column("provider_user_id", sa.String(), nullable=False),
            sa.Column("provider_email", sa.String(), nullable=True),
            sa.Column("provider_name", sa.String(), nullable=True),
            sa.Column("provider_avatar_url", sa.String(), nullable=True),
            sa.Column("metadata_json", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], name="fk_user_identity_user_id"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("provider_code", "provider_user_id", name="uq_user_identity_provider"),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("user_identity")}
    if "idx_user_identity_user_id" not in existing_indexes:
        op.create_index("idx_user_identity_user_id", "user_identity", ["user_id"])
    if "idx_user_identity_provider" not in existing_indexes:
        op.create_index("idx_user_identity_provider", "user_identity", ["provider_code", "provider_user_id"])

    # --- oauthstate: add purpose column (idempotent) ---
    existing_cols = {c["name"] for c in inspector.get_columns("oauthstate")}
    if "purpose" not in existing_cols:
        op.add_column(
            "oauthstate",
            sa.Column("purpose", sa.String(), nullable=True, server_default="integration"),
        )


def downgrade() -> None:
    op.drop_column("oauthstate", "purpose")
    op.drop_index("idx_user_identity_provider", table_name="user_identity")
    op.drop_index("idx_user_identity_user_id", table_name="user_identity")
    op.drop_table("user_identity")
