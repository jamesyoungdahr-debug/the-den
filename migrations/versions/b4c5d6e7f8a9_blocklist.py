"""M19: blocklist and download failure tracking

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.add_column(sa.Column("failure_reason", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_progress", sa.Float(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("last_progress_at", sa.DateTime(), nullable=True))
    op.create_table("blocklist", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("info_hash", sa.String(), nullable=True), sa.Column("release_title", sa.String(), nullable=False), sa.Column("reason", sa.String(), nullable=False), sa.Column("movie_id", sa.Integer(), sa.ForeignKey("movies.id", ondelete="SET NULL"), nullable=True), sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="SET NULL"), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.create_index("ix_blocklist_info_hash", "blocklist", ["info_hash"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_blocklist_info_hash", table_name="blocklist")
    op.drop_table("blocklist")
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.drop_column("failure_reason")
        batch_op.drop_column("last_progress")
        batch_op.drop_column("last_progress_at")
