"""M11g: request quotas, sign-in-required toggle, request available_at

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-12 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('settings') as batch:
        batch.add_column(sa.Column('request_movie_limit', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('request_series_limit', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('request_limit_days', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('auth_required', sa.Boolean(), nullable=True))
    with op.batch_alter_table('media_requests') as batch:
        batch.add_column(sa.Column('available_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('media_requests') as batch:
        batch.drop_column('available_at')
    with op.batch_alter_table('settings') as batch:
        batch.drop_column('auth_required')
        batch.drop_column('request_limit_days')
        batch.drop_column('request_series_limit')
        batch.drop_column('request_movie_limit')
