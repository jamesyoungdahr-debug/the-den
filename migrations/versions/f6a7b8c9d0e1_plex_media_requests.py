"""plex_media (M11e scan), media_requests + episodes.monitored (M11f requests)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-12 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'plex_media',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('rating_key', sa.String(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=True),
        sa.Column('tvdb_id', sa.Integer(), nullable=True),
        sa.Column('imdb_id', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('seasons', sa.String(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rating_key'),
    )
    op.create_index('ix_plex_media_tmdb_id', 'plex_media', ['tmdb_id'])
    op.create_index('ix_plex_media_tvdb_id', 'plex_media', ['tvdb_id'])

    op.create_table(
        'media_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('tmdb_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('poster_path', sa.String(), nullable=True),
        sa.Column('seasons', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column('requested_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('decided_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('movie_id', sa.Integer(), sa.ForeignKey('movies.id'), nullable=True),
        sa.Column('series_id', sa.Integer(), sa.ForeignKey('series.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_media_requests_tmdb_id', 'media_requests', ['tmdb_id'])

    with op.batch_alter_table('episodes') as batch_op:
        batch_op.add_column(sa.Column('monitored', sa.Boolean(), nullable=False, server_default=sa.true()))

    with op.batch_alter_table('settings') as batch_op:
        batch_op.add_column(sa.Column('plex_scan_interval_minutes', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('plex_last_scan_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('plex_last_scan_result', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('plex_last_scan_result')
        batch_op.drop_column('plex_last_scan_at')
        batch_op.drop_column('plex_scan_interval_minutes')
    with op.batch_alter_table('episodes') as batch_op:
        batch_op.drop_column('monitored')
    op.drop_index('ix_media_requests_tmdb_id', table_name='media_requests')
    op.drop_table('media_requests')
    op.drop_index('ix_plex_media_tvdb_id', table_name='plex_media')
    op.drop_index('ix_plex_media_tmdb_id', table_name='plex_media')
    op.drop_table('plex_media')
