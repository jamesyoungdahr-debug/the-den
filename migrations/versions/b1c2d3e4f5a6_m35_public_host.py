"""M35: settings.public_host (the name remote apps use; the self-signed certificate covers it)

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-09-14 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('settings') as batch_op:
        batch_op.add_column(sa.Column('public_host', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('public_host')
