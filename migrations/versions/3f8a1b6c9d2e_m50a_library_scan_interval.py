"""M50a: Settings.library_scan_interval_minutes

Revision ID: 3f8a1b6c9d2e
Revises: 7b3c9d1e5f2a
Create Date: 2026-09-15 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f8a1b6c9d2e'
down_revision: Union[str, Sequence[str], None] = '7b3c9d1e5f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('settings', sa.Column('library_scan_interval_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('settings', 'library_scan_interval_minutes')
