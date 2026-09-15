"""M49: media_probes and playback_states (direct play in the web UI)

Revision ID: 4d9e2a7c1b35
Revises: c2d3e4f5a6b7
Create Date: 2026-09-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d9e2a7c1b35'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'media_probes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('mtime_ns', sa.BigInteger(), nullable=False),
        sa.Column('probed_at', sa.DateTime(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path', name='uq_media_probes_file_path'),
    )
    op.create_table(
        'playback_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('item_kind', sa.String(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('position_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duration_ms', sa.Integer(), server_default='0', nullable=False),
        sa.Column('played', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('play_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_played_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('device', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_playback_states_user_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'item_kind', 'item_id', name='uq_playback_state_item'),
    )
    op.create_index('ix_playback_states_user_id', 'playback_states', ['user_id'])
    op.create_index('ix_playback_states_user_updated', 'playback_states', ['user_id', 'updated_at'])


def downgrade() -> None:
    op.drop_index('ix_playback_states_user_updated', table_name='playback_states')
    op.drop_index('ix_playback_states_user_id', table_name='playback_states')
    op.drop_table('playback_states')
    op.drop_table('media_probes')
