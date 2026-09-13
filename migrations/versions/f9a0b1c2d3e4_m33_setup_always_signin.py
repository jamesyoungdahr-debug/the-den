"""M33: sign-in always required and a first-run setup (drop settings.auth_required, add server_name and setup_completed_at)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-09-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.add_column(sa.Column('server_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('setup_completed_at', sa.DateTime(), nullable=True))
        batch_op.drop_column('auth_required')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.add_column(sa.Column('auth_required', sa.Boolean(), nullable=True))
        batch_op.drop_column('setup_completed_at')
        batch_op.drop_column('server_name')