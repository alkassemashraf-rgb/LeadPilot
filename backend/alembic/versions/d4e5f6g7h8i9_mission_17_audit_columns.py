"""mission_17_audit_columns

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-26 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "d4e5f6g7h8i9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6g7h8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make actor_user_id nullable (for failed login where user unknown)
    # SQLite >=3.35 supports ALTER COLUMN via batch mode
    with op.batch_alter_table("adminauditlog") as batch_op:
        batch_op.alter_column("actor_user_id", existing_type=sa.Uuid(), nullable=True)

    # Add new Mission 17 columns
    op.add_column("adminauditlog", sa.Column("actor_type", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("agency_id", sa.Uuid(), nullable=True))
    op.add_column("adminauditlog", sa.Column("outcome", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("ip_address", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("user_agent", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("request_path", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("request_method", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("error_code", sa.String(), nullable=True))
    op.add_column("adminauditlog", sa.Column("error_message", sa.String(), nullable=True))

    # New composite indexes
    op.create_index("idx_audit_agency_created", "adminauditlog", ["agency_id", "created_at"])
    op.create_index("idx_audit_outcome", "adminauditlog", ["outcome", "created_at"])
    op.create_index("idx_audit_actor_type", "adminauditlog", ["actor_type", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_actor_type", table_name="adminauditlog")
    op.drop_index("idx_audit_outcome", table_name="adminauditlog")
    op.drop_index("idx_audit_agency_created", table_name="adminauditlog")

    op.drop_column("adminauditlog", "error_message")
    op.drop_column("adminauditlog", "error_code")
    op.drop_column("adminauditlog", "request_method")
    op.drop_column("adminauditlog", "request_path")
    op.drop_column("adminauditlog", "user_agent")
    op.drop_column("adminauditlog", "ip_address")
    op.drop_column("adminauditlog", "outcome")
    op.drop_column("adminauditlog", "agency_id")
    op.drop_column("adminauditlog", "actor_type")

    with op.batch_alter_table("adminauditlog") as batch_op:
        batch_op.alter_column("actor_user_id", existing_type=sa.Uuid(), nullable=False)
