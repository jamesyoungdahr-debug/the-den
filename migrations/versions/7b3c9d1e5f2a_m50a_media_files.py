"""M50a: media_files, one row per video file in the library folders

Revision ID: 7b3c9d1e5f2a
Revises: 4d9e2a7c1b35
Create Date: 2026-09-15 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b3c9d1e5f2a'
down_revision: Union[str, Sequence[str], None] = '4d9e2a7c1b35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'media_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('media_type', sa.String(), nullable=False),
        sa.Column('movie_id', sa.Integer(), nullable=True),
        sa.Column('episode_id', sa.Integer(), nullable=True),
        sa.Column('root_folder_id', sa.Integer(), nullable=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=True),
        sa.Column('mtime_ns', sa.BigInteger(), nullable=True),
        sa.Column('quality', sa.String(), nullable=True),
        sa.Column('score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('matched', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('missing', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('movie_id IS NULL OR episode_id IS NULL', name='ck_media_files_one_owner'),
        sa.ForeignKeyConstraint(['movie_id'], ['movies.id'], name='fk_media_files_movie_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], name='fk_media_files_episode_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['root_folder_id'], ['root_folders.id'], name='fk_media_files_root_folder_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path', name='uq_media_files_path'),
    )
    op.create_index('ix_media_files_movie_id', 'media_files', ['movie_id'])
    op.create_index('ix_media_files_episode_id', 'media_files', ['episode_id'])
    op.create_index('ix_media_files_missing', 'media_files', ['missing'])

    # Backfill from the single file_path each title carries today, so playback keeps working.
    # INSERT OR IGNORE because path is unique and a duplicate must not abort the migration.
    # size and mtime_ns stay NULL: the migration must not touch the filesystem.
    op.execute(
        """
        INSERT OR IGNORE INTO media_files
            (media_type, movie_id, episode_id, path, size, mtime_ns, matched, missing, added_at, last_seen_at)
        SELECT 'movie', id, NULL, file_path, NULL, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM movies
        WHERE file_path IS NOT NULL AND TRIM(file_path) <> ''
        """
    )
    op.execute(
        """
        INSERT OR IGNORE INTO media_files
            (media_type, movie_id, episode_id, path, size, mtime_ns, matched, missing, added_at, last_seen_at)
        SELECT 'tv', NULL, id, file_path, NULL, NULL, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM episodes
        WHERE file_path IS NOT NULL AND TRIM(file_path) <> ''
        """
    )


def downgrade() -> None:
    op.drop_index('ix_media_files_missing', table_name='media_files')
    op.drop_index('ix_media_files_episode_id', table_name='media_files')
    op.drop_index('ix_media_files_movie_id', table_name='media_files')
    op.drop_table('media_files')
