"""Mission 30 — WhatsApp Cloud Production Hardening

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

revision = "j0k1l2m3n4o5"
down_revision = "i9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Message lifecycle fields
    op.add_column("message", sa.Column("delivered_at", sa.DateTime, nullable=True))
    op.add_column("message", sa.Column("read_at", sa.DateTime, nullable=True))
    op.add_column("message", sa.Column("failure_code", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("message", "failure_code")
    op.drop_column("message", "read_at")
    op.drop_column("message", "delivered_at")
