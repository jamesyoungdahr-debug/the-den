"""M51: one-time sign-in links

Revision ID: 8c4d2e6f9a13
Revises: 3f8a1b6c9d2e
Create Date: 2026-09-15 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c4d2e6f9a13'
down_revision: Union[str, Sequence[str], None] = '3f8a1b6c9d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('sign_in_token_hash', sa.String(), nullable=True))
    op.add_column('users', sa.Column('sign_in_expires_at', sa.DateTime(), nullable=True))
    # Unique so two accounts can never hold the same link. SQLite allows many NULLs in a unique
    # index, which is what every user without an outstanding link has.
    op.create_index('ix_users_sign_in_token_hash', 'users', ['sign_in_token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_sign_in_token_hash', table_name='users')
    op.drop_column('users', 'sign_in_expires_at')
    op.drop_column('users', 'sign_in_token_hash')
