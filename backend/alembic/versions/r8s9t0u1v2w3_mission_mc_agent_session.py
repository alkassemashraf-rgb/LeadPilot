"""Mission M-C: add agent_session table for persistent ADK sessions

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "r8s9t0u1v2w3"
down_revision = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "agent_session" not in inspector.get_table_names():
        op.create_table(
            "agent_session",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "conversation_id",
                sa.Uuid(),
                sa.ForeignKey("conversation.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("app_name", sa.String(), nullable=False, server_default="leadpilot"),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("state", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("events", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("agent_session")
