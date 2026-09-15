"""M51: the watchlist_items table

Revision ID: 9d5e3f7a1b26
Revises: 8c4d2e6f9a13
Create Date: 2026-09-15 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d5e3f7a1b26'
down_revision: Union[str, Sequence[str], None] = '8c4d2e6f9a13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'watchlist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('poster_path', sa.String(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_watchlist_items_user_id', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'media_type', 'tmdb_id', name='uq_watchlist_item'),
    )
    op.create_index('ix_watchlist_items_user_id', 'watchlist_items', ['user_id'])
    op.create_index('ix_watchlist_items_tmdb_id', 'watchlist_items', ['tmdb_id'])


def downgrade() -> None:
    op.drop_index('ix_watchlist_items_tmdb_id', table_name='watchlist_items')
    op.drop_index('ix_watchlist_items_user_id', table_name='watchlist_items')
    op.drop_table('watchlist_items')
