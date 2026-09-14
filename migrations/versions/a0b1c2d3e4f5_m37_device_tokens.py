"""M37: per-device sign-in tokens (device_tokens; each users.api_token moves in as one hashed device)

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-09-14 17:00:00.000000

"""
import hashlib
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, Sequence[str], None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create device_tokens, move every existing users.api_token in as a hashed device, then drop the
    plaintext column. Apps that already hold a token keep working."""
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False, unique=True),
        sa.Column('token_prefix', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_device_tokens_user_id', 'device_tokens', ['user_id'])

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, api_token FROM users WHERE api_token IS NOT NULL AND api_token != ''")).fetchall()
    if rows:
        device_tokens = sa.table(
            'device_tokens',
            sa.column('user_id', sa.Integer), sa.column('name', sa.String), sa.column('platform', sa.String),
            sa.column('token_hash', sa.String), sa.column('token_prefix', sa.String), sa.column('created_at', sa.DateTime),
        )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        op.bulk_insert(device_tokens, [
            {
                'user_id': user_id, 'name': 'Token from before device tokens', 'platform': 'other',
                'token_hash': hashlib.sha256(token.encode('utf-8')).hexdigest(), 'token_prefix': token[:8], 'created_at': now,
            }
            for user_id, token in rows
        ])

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('api_token')


def downgrade() -> None:
    """Put users.api_token back, empty. Tokens were only stored hashed, so none can be restored:
    every app has to sign in again after a downgrade."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('api_token', sa.String(), nullable=True))
    op.drop_index('ix_device_tokens_user_id', table_name='device_tokens')
    op.drop_table('device_tokens')
