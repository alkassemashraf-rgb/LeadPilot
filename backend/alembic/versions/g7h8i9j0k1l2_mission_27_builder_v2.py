"""Mission 27 — Automation Builder v2 + Template Catalog Foundation

Revision ID: g7h8i9j0k1l2
Revises: e5f6g7h8i9j0
Create Date: 2026-02-28

Adds:
- flow.published_version_id (FK to flowversion, use_alter=True circular ref)
- flowdraft table (one per flow, editable builder graph)
- automationtemplate table (global admin-managed templates)
- automationtemplateversion table (immutable template snapshots)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "g7h8i9j0k1l2"
down_revision = "e5f6g7h8i9j0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # 1. Add published_version_id to flow table
    op.add_column(
        "flow",
        sa.Column("published_version_id", sa.Uuid(), nullable=True)
    )
    op.create_index("ix_flow_published_version_id", "flow", ["published_version_id"])
    # SQLite does not support ALTER TABLE ADD CONSTRAINT — skip FK for SQLite
    if not is_sqlite:
        op.create_foreign_key(
            "fk_flow_published_version_id",
            "flow", "flowversion",
            ["published_version_id"], ["id"],
            use_alter=True
        )

    # 2. Backfill published_version_id for existing flows that have published versions
    op.execute("""
        UPDATE flow
        SET published_version_id = (
            SELECT fv.id FROM flowversion fv
            WHERE fv.flow_id = flow.id
              AND fv.is_published = TRUE
            ORDER BY fv.version_number DESC
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM flowversion fv2
            WHERE fv2.flow_id = flow.id
              AND fv2.is_published = TRUE
        )
    """)

    # 3. Create flowdraft table
    op.create_table(
        "flowdraft",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("flow_id", sa.Uuid(), nullable=False),
        sa.Column("builder_graph_json", sa.JSON(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("last_validation_errors", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["flow_id"], ["flow.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("flow_id", name="uq_flowdraft_flow_id"),
    )
    op.create_index("ix_flowdraft_workspace_id", "flowdraft", ["workspace_id"])
    op.create_index("idx_flowdraft_ws_updated", "flowdraft", ["workspace_id", "updated_at"])

    # 4. Create automationtemplate table
    op.create_table(
        "automationtemplate",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("industry_tags", sa.JSON(), nullable=False),
        sa.Column("platforms", sa.JSON(), nullable=False),
        sa.Column("required_integrations", sa.JSON(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_automationtemplate_slug"),
    )
    op.create_index("ix_automationtemplate_slug", "automationtemplate", ["slug"], unique=True)
    op.create_index("ix_automationtemplate_name", "automationtemplate", ["name"])
    op.create_index("ix_automationtemplate_category", "automationtemplate", ["category"])
    op.create_index("ix_automationtemplate_is_featured", "automationtemplate", ["is_featured"])
    op.create_index("ix_automationtemplate_is_active", "automationtemplate", ["is_active"])
    op.create_index("idx_template_active_featured", "automationtemplate", ["is_active", "is_featured"])

    # 5. Create automationtemplateversion table
    op.create_table(
        "automationtemplateversion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("builder_graph_json", sa.JSON(), nullable=False),
        sa.Column("translated_definition_json", sa.JSON(), nullable=True),
        sa.Column("changelog", sa.String(), nullable=True),
        sa.Column("created_by_admin_id", sa.Uuid(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["template_id"], ["automationtemplate.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automationtemplateversion_template_id", "automationtemplateversion", ["template_id"])
    op.create_index("ix_automationtemplateversion_is_published", "automationtemplateversion", ["is_published"])
    op.create_index("idx_atv_template_ver", "automationtemplateversion", ["template_id", "version_number"])
    op.create_index("idx_atv_template_published", "automationtemplateversion", ["template_id", "is_published"])


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Reverse order
    op.drop_index("idx_atv_template_published", table_name="automationtemplateversion")
    op.drop_index("idx_atv_template_ver", table_name="automationtemplateversion")
    op.drop_index("ix_automationtemplateversion_is_published", table_name="automationtemplateversion")
    op.drop_index("ix_automationtemplateversion_template_id", table_name="automationtemplateversion")
    op.drop_table("automationtemplateversion")

    op.drop_index("idx_template_active_featured", table_name="automationtemplate")
    op.drop_index("ix_automationtemplate_is_active", table_name="automationtemplate")
    op.drop_index("ix_automationtemplate_is_featured", table_name="automationtemplate")
    op.drop_index("ix_automationtemplate_category", table_name="automationtemplate")
    op.drop_index("ix_automationtemplate_name", table_name="automationtemplate")
    op.drop_index("ix_automationtemplate_slug", table_name="automationtemplate")
    op.drop_table("automationtemplate")

    op.drop_index("idx_flowdraft_ws_updated", table_name="flowdraft")
    op.drop_index("ix_flowdraft_workspace_id", table_name="flowdraft")
    op.drop_table("flowdraft")

    if not is_sqlite:
        op.drop_constraint("fk_flow_published_version_id", "flow", type_="foreignkey")
    op.drop_index("ix_flow_published_version_id", table_name="flow")
    op.drop_column("flow", "published_version_id")
