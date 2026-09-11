"""add Plex settings (M11c Plex login)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-11 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    sa.Column('plex_token', sa.String(), nullable=True),
    sa.Column('plex_owner_id', sa.Integer(), nullable=True),
    sa.Column('plex_owner_username', sa.String(), nullable=True),
    sa.Column('plex_server_name', sa.String(), nullable=True),
    sa.Column('plex_machine_id', sa.String(), nullable=True),
    sa.Column('plex_url', sa.String(), nullable=True),
    sa.Column('plex_sections', sa.String(), nullable=True),
    sa.Column('plex_allow_any_account', sa.Boolean(), nullable=True),
)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        for column in COLUMNS:
            batch_op.add_column(column)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        for column in reversed(COLUMNS):
            batch_op.drop_column(column.name)
