"""E5: per-title history events

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-09-13 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "history_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("release_title", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id"), nullable=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id"), nullable=True),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=True),
        sa.Column("season_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_history_events_movie_id", "history_events", ["movie_id"])
    op.create_index("ix_history_events_episode_id", "history_events", ["episode_id"])
    op.create_index("ix_history_events_series_id", "history_events", ["series_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_history_events_series_id", table_name="history_events")
    op.drop_index("ix_history_events_episode_id", table_name="history_events")
    op.drop_index("ix_history_events_movie_id", table_name="history_events")
    op.drop_table("history_events")
