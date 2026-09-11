"""built-in torrent engine: replace qBittorrent settings, track downloads by info-hash

Revision ID: b7e2f1c4d9a0
Revises: 93e0b8e54d80
Create Date: 2026-09-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f1c4d9a0'
down_revision: Union[str, Sequence[str], None] = '93e0b8e54d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('qbit_url')
        batch_op.drop_column('qbit_username')
        batch_op.drop_column('qbit_password')
        batch_op.add_column(sa.Column('downloads_root', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('torrent_port', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('download_rate_limit_kib', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('upload_rate_limit_kib', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('seed_ratio_limit', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('seed_time_limit_minutes', sa.Integer(), nullable=True))

    with op.batch_alter_table('download_records') as batch_op:
        # `category` was the qBittorrent-side tag we tracked downloads by; the built-in
        # engine tracks by info-hash. Pre-existing un-imported records lose their link to
        # a download client either way, so nothing is preserved from it.
        batch_op.drop_column('category')
        batch_op.add_column(sa.Column('info_hash', sa.String(), nullable=True))
        batch_op.create_index('ix_download_records_info_hash', ['info_hash'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('download_records') as batch_op:
        batch_op.drop_index('ix_download_records_info_hash')
        batch_op.drop_column('info_hash')
        batch_op.add_column(sa.Column('category', sa.String(), nullable=False, server_default=''))

    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('seed_time_limit_minutes')
        batch_op.drop_column('seed_ratio_limit')
        batch_op.drop_column('upload_rate_limit_kib')
        batch_op.drop_column('download_rate_limit_kib')
        batch_op.drop_column('torrent_port')
        batch_op.drop_column('downloads_root')
        batch_op.add_column(sa.Column('qbit_password', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('qbit_username', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('qbit_url', sa.String(), nullable=True))
