"""M18: upgrades - file quality/score on titles, score on downloads, profile upgrade_until_score

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-12 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("quality_profiles") as batch_op:
        batch_op.add_column(sa.Column("upgrade_until_score", sa.Integer(), server_default="0", nullable=False))
    with op.batch_alter_table("movies") as batch_op:
        batch_op.add_column(sa.Column("file_quality", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("file_score", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("file_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_upgrade_search", sa.DateTime(), nullable=True))
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.add_column(sa.Column("file_quality", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("file_score", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("file_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_upgrade_search", sa.DateTime(), nullable=True))
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.add_column(sa.Column("quality", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("score", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("upgrade", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.drop_column("quality")
        batch_op.drop_column("score")
        batch_op.drop_column("upgrade")
    with op.batch_alter_table("episodes") as batch_op:
        batch_op.drop_column("file_quality")
        batch_op.drop_column("file_score")
        batch_op.drop_column("file_path")
        batch_op.drop_column("last_upgrade_search")
    with op.batch_alter_table("movies") as batch_op:
        batch_op.drop_column("file_quality")
        batch_op.drop_column("file_score")
        batch_op.drop_column("file_path")
        batch_op.drop_column("last_upgrade_search")
    with op.batch_alter_table("quality_profiles") as batch_op:
        batch_op.drop_column("upgrade_until_score")
