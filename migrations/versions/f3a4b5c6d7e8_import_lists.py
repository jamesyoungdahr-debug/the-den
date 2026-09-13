"""E1: import lists (TMDB list, Plex watchlist)

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-09-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, Sequence[str], None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "import_lists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("config", sa.String(), nullable=True),
        sa.Column("quality_profile_id", sa.Integer(), sa.ForeignKey("quality_profiles.id"), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("last_result", sa.String(), nullable=True),
    )
    columns = [sa.Column("import_list_interval_minutes", sa.Integer(), nullable=True)]
    with op.batch_alter_table('settings') as batch_op:
        for column in columns:
            batch_op.add_column(column)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('import_list_interval_minutes')
    op.drop_table("import_lists")
