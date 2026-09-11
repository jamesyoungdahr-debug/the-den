"""add series.tmdb_id (M11d Discover)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('series') as batch_op:
        batch_op.add_column(sa.Column('tmdb_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_series_tmdb_id', ['tmdb_id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('series') as batch_op:
        batch_op.drop_index('ix_series_tmdb_id')
        batch_op.drop_column('tmdb_id')
