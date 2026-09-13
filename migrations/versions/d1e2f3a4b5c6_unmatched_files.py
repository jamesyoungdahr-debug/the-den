"""M23: unmatched download files

Revision ID: d1e2f3a4b5c6
Revises: c5d6e7f8a9b0
Create Date: 2026-09-13 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.add_column(sa.Column("unmatched_files", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("download_records") as batch_op:
        batch_op.drop_column("unmatched_files")