"""Mission 31 — Meta Platform: Instagram DM, Messenger, Lead Ads

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("channelidentity", sa.Column("channel", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("channelidentity", "channel")
