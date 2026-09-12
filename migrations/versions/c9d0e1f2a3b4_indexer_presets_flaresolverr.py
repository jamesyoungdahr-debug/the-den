"""M12: indexer presets + native public trackers; FlareSolverr/Byparr URL

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-09-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('indexers') as batch:
        # torznab | newznab | a native slug (app/indexers/native.py); existing rows keep their protocol
        batch.add_column(sa.Column('implementation', sa.String(), nullable=True))
        # catalog preset the row was created from (app/indexers/catalog.py), for the UI
        batch.add_column(sa.Column('preset', sa.String(), nullable=True))
    op.execute("UPDATE indexers SET implementation = protocol WHERE implementation IS NULL")
    with op.batch_alter_table('settings') as batch:
        batch.add_column(sa.Column('flaresolverr_url', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch:
        batch.drop_column('flaresolverr_url')
    with op.batch_alter_table('indexers') as batch:
        batch.drop_column('preset')
        batch.drop_column('implementation')
