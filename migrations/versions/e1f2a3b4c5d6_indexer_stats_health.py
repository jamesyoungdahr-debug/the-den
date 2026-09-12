"""M16: indexer_stats and health_issues

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "indexer_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("indexer_id", sa.Integer(), sa.ForeignKey("indexers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.String(), nullable=False),  # YYYY-MM-DD, UTC
        sa.Column("searches", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(), nullable=True),
    )
    op.create_index("ix_indexer_stats_indexer_day", "indexer_stats", ["indexer_id", "day"], unique=True)

    op.create_table(
        "health_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),  # warning | error
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_indexer_stats_indexer_day", table_name="indexer_stats")
    op.drop_table("indexer_stats")
    op.drop_table("health_issues")
