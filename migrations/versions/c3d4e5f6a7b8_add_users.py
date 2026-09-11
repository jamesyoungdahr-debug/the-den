"""add users table (M11b accounts)

Revision ID: c3d4e5f6a7b8
Revises: b7e2f1c4d9a0
Create Date: 2026-09-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b7e2f1c4d9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('plex_id', sa.Integer(), nullable=True),
        sa.Column('plex_username', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False, server_default='user'),
        sa.Column('auto_approve', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('movie_limit', sa.Integer(), nullable=True),
        sa.Column('series_limit', sa.Integer(), nullable=True),
        sa.Column('limit_days', sa.Integer(), nullable=True),
        sa.Column('api_token', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('plex_id'),
        sa.UniqueConstraint('api_token'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users')
