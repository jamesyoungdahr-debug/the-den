"""M17: custom formats and profile format scores

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-12 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table("custom_formats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rules", sa.Text(), server_default="[]", nullable=False),
        sa.Column("builtin", sa.Boolean(), server_default="0", nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table("profile_format_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("quality_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format_id", sa.Integer(), sa.ForeignKey("custom_formats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Integer(), server_default="0", nullable=False),
        sa.UniqueConstraint("profile_id", "format_id", name="uq_profile_format"),
    )
    with op.batch_alter_table("quality_profiles") as batch_op:
        batch_op.add_column(sa.Column("min_format_score", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("quality_profiles") as batch_op:
        batch_op.drop_column("min_format_score")
    op.drop_table("profile_format_scores")
    op.drop_table("custom_formats")
