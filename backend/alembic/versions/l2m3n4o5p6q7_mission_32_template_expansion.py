"""Mission 32 — Template variables, usage stats, flow source tracking

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
"""
from alembic import op
import sqlalchemy as sa

revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add template source columns to flow
    op.add_column("flow", sa.Column("source_template_id", sa.String, nullable=True))
    op.add_column("flow", sa.Column("source_template_version_id", sa.String, nullable=True))
    op.create_index("idx_flow_source_template", "flow", ["source_template_id"])

    # 2. Create templatevariable table
    op.create_table(
        "templatevariable",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("template_version_id", sa.String, sa.ForeignKey("automationtemplateversion.id"), nullable=False),
        sa.Column("key", sa.String, nullable=False),
        sa.Column("label", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("var_type", sa.String, nullable=False, server_default="text"),
        sa.Column("required", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("default_value", sa.String, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint("template_version_id", "key", name="uq_tmplvar_version_key"),
    )
    op.create_index("idx_tmplvar_version", "templatevariable", ["template_version_id", "sort_order"])

    # 3. Create flowtemplatevariablevalue table
    op.create_table(
        "flowtemplatevariablevalue",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("flow_id", sa.String, sa.ForeignKey("flow.id"), nullable=False),
        sa.Column("template_variable_id", sa.String, sa.ForeignKey("templatevariable.id"), nullable=False),
        sa.Column("value", sa.String, nullable=True),
        sa.UniqueConstraint("flow_id", "template_variable_id", name="uq_ftvv_flow_var"),
    )
    op.create_index("idx_ftvv_flow", "flowtemplatevariablevalue", ["flow_id"])

    # 4. Create templateusagestat table
    op.create_table(
        "templateusagestat",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("template_id", sa.String, sa.ForeignKey("automationtemplate.id"), nullable=False, unique=True),
        sa.Column("clone_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("publish_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("active_flows_count", sa.Integer, nullable=False, server_default=sa.text("0")),
    )
    op.create_index("idx_tus_template", "templateusagestat", ["template_id"])


def downgrade() -> None:
    op.drop_index("idx_tus_template", "templateusagestat")
    op.drop_table("templateusagestat")
    op.drop_index("idx_ftvv_flow", "flowtemplatevariablevalue")
    op.drop_table("flowtemplatevariablevalue")
    op.drop_index("idx_tmplvar_version", "templatevariable")
    op.drop_table("templatevariable")
    op.drop_index("idx_flow_source_template", "flow")
    op.drop_column("flow", "source_template_version_id")
    op.drop_column("flow", "source_template_id")
