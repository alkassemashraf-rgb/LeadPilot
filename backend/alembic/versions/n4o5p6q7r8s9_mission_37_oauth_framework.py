"""Mission 37 — Universal OAuth Provider Framework

Creates oauthprovider, oauthconnection, and oauthstate tables.

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
"""
from alembic import op
import sqlalchemy as sa

revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauthprovider",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("auth_url", sa.String(), nullable=False),
        sa.Column("token_url", sa.String(), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("supports_refresh_token", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_code"),
    )
    op.create_index("idx_oauth_provider_code", "oauthprovider", ["provider_code"])

    op.create_table(
        "oauthconnection",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("provider_code", sa.String(), nullable=False),
        sa.Column("external_account_id", sa.String(), nullable=True),
        sa.Column("external_account_name", sa.String(), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("token_type", sa.String(), nullable=True),
        sa.Column("scopes_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_oauth_conn_workspace_provider", "oauthconnection", ["workspace_id", "provider_code"])
    op.create_index("idx_oauth_conn_user_provider", "oauthconnection", ["user_id", "provider_code"])

    op.create_table(
        "oauthstate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider_code", sa.String(), nullable=False),
        sa.Column("state_token", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("redirect_after", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_token"),
    )
    op.create_index("idx_oauth_state_token", "oauthstate", ["state_token"])
    op.create_index("idx_oauth_state_expires", "oauthstate", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_oauth_state_expires", table_name="oauthstate")
    op.drop_index("idx_oauth_state_token", table_name="oauthstate")
    op.drop_table("oauthstate")

    op.drop_index("idx_oauth_conn_user_provider", table_name="oauthconnection")
    op.drop_index("idx_oauth_conn_workspace_provider", table_name="oauthconnection")
    op.drop_table("oauthconnection")

    op.drop_index("idx_oauth_provider_code", table_name="oauthprovider")
    op.drop_table("oauthprovider")
