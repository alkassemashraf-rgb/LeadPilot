"""Mission M-B: add qualification_status and intent to contact

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "q7r8s9t0u1v2"
down_revision = "p6q7r8s9t0u1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("contact")}
    if "qualification_status" not in existing_cols:
        op.add_column("contact", sa.Column("qualification_status", sa.String(), nullable=True))
    if "intent" not in existing_cols:
        op.add_column("contact", sa.Column("intent", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("contact", "intent")
    op.drop_column("contact", "qualification_status")
