"""E7: usenet via SABnzbd (settings, download_records.download_client)

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-09-13 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, Sequence[str], None] = 'b5c6d7e8f9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    columns = [
        sa.Column("sabnzbd_url", sa.String(), nullable=True),
        sa.Column("sabnzbd_api_key", sa.String(), nullable=True),
    ]
    with op.batch_alter_table('settings') as batch_op:
        for column in columns:
            batch_op.add_column(column)

    download_client = sa.Column(
        "download_client",
        sa.String(),
        nullable=False,
        server_default="torrent",
    )
    with op.batch_alter_table('download_records') as batch_op:
        batch_op.add_column(download_client)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('download_records') as batch_op:
        batch_op.drop_column('download_client')

    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('sabnzbd_api_key')
        batch_op.drop_column('sabnzbd_url')
