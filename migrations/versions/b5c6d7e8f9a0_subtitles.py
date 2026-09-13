"""E6: subtitles (OpenSubtitles API key, language preference)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-09-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5c6d7e8f9a0'
down_revision: Union[str, Sequence[str], None] = 'a4b5c6d7e8f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    columns = [
        sa.Column("opensubtitles_api_key", sa.String(), nullable=True),
        sa.Column("subtitle_languages", sa.String(), nullable=True),
    ]
    with op.batch_alter_table('settings') as batch_op:
        for column in columns:
            batch_op.add_column(column)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('settings') as batch_op:
        batch_op.drop_column('subtitle_languages')
        batch_op.drop_column('opensubtitles_api_key')
