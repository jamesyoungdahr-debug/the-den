"""E2: root folders (multiple libraries per media type)

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-09-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, Sequence[str], None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "root_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    with op.batch_alter_table('movies') as batch_op:
        batch_op.add_column(sa.Column("root_folder_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_movies_root_folder_id", "root_folders", ["root_folder_id"], ["id"])
    with op.batch_alter_table('series') as batch_op:
        batch_op.add_column(sa.Column("root_folder_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_series_root_folder_id", "root_folders", ["root_folder_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('series') as batch_op:
        batch_op.drop_constraint("fk_series_root_folder_id", type_="foreignkey")
        batch_op.drop_column('root_folder_id')
    with op.batch_alter_table('movies') as batch_op:
        batch_op.drop_constraint("fk_movies_root_folder_id", type_="foreignkey")
        batch_op.drop_column('root_folder_id')
    op.drop_table("root_folders")
