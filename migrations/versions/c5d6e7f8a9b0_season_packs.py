"""M20: season pack download records

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-13 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.add_column(sa.Column("series_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("season_number", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_download_records_series_id", "series", ["series_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.drop_constraint("fk_download_records_series_id", type_="foreignkey")
        batch_op.drop_column("season_number")
        batch_op.drop_column("series_id")
