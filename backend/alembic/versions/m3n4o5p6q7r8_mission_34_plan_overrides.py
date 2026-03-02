"""Mission 34 — Admin Plan Overrides (time-bound plan grants with expiry + audit)

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
"""
from alembic import op
import sqlalchemy as sa

revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planoverride",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspace.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"]),
        sa.ForeignKeyConstraint(["revoked_by_admin_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["created_by_admin_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_plan_override_ws_status", "planoverride", ["workspace_id", "status"])
    op.create_index("idx_plan_override_ends_at", "planoverride", ["ends_at"])


def downgrade() -> None:
    op.drop_index("idx_plan_override_ends_at", table_name="planoverride")
    op.drop_index("idx_plan_override_ws_status", table_name="planoverride")
    op.drop_table("planoverride")
