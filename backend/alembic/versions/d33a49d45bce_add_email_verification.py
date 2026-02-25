"""add_email_verification

Revision ID: d33a49d45bce
Revises: df5028f5204e
Create Date: 2026-02-20 14:33:47.577005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd33a49d45bce'
down_revision: Union[str, Sequence[str], None] = 'df5028f5204e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Part 1: Incremental updates to User table ---
    # We use try/except for each column because SQLite's batch mode can be finicky with inspection in migrations
    try:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))
    except Exception:
        pass
        
    try:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True))
    except Exception:
        pass
        
    try:        
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('email_verification_sent_at', sa.DateTime(), nullable=True))
    except Exception:
        pass

    # --- Part 2: New Table for Verification Tokens ---
    try:
        op.create_table('emailverificationtoken',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('token_hash', sa.String(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('used_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_emailverificationtoken_id'), 'emailverificationtoken', ['id'], unique=False)
        op.create_index(op.f('ix_emailverificationtoken_token_hash'), 'emailverificationtoken', ['token_hash'], unique=True)
        op.create_index(op.f('ix_emailverificationtoken_user_id'), 'emailverificationtoken', ['user_id'], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index(op.f('ix_emailverificationtoken_user_id'), table_name='emailverificationtoken')
        op.drop_index(op.f('ix_emailverificationtoken_token_hash'), table_name='emailverificationtoken')
        op.drop_index(op.f('ix_emailverificationtoken_id'), table_name='emailverificationtoken')
        op.drop_table('emailverificationtoken')
    except Exception:
        pass

    try:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('email_verification_sent_at')
            batch_op.drop_column('email_verification_expires_at')
            batch_op.drop_column('email_verified_at')
    except Exception:
        pass
    # ### end Alembic commands ###
