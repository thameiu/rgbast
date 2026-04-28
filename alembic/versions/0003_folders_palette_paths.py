"""Add folder table and palette folder paths

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BIG = sa.BigInteger()


def upgrade() -> None:
    op.create_table(
        "folder",
        sa.Column("id", _BIG, primary_key=True, nullable=False),
        sa.Column("user_id", _BIG, sa.ForeignKey("user.id"), nullable=False),
        sa.Column("parent_folder_id", _BIG, sa.ForeignKey("folder.id"), nullable=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_folder_user_id", "folder", ["user_id"], unique=False)
    op.create_index("ix_folder_parent_folder_id", "folder", ["parent_folder_id"], unique=False)
    op.create_index("ix_folder_name", "folder", ["name"], unique=False)
    op.create_index(
        "uq_folder_user_parent_name",
        "folder",
        ["user_id", "parent_folder_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_folder_id IS NOT NULL"),
    )
    op.create_index(
        "uq_folder_user_root_name",
        "folder",
        ["user_id", "name"],
        unique=True,
        postgresql_where=sa.text("parent_folder_id IS NULL"),
    )

    op.add_column("palette", sa.Column("folder_id", _BIG, nullable=True))
    op.create_foreign_key(
        "fk_palette_folder_id_folder",
        "palette",
        "folder",
        ["folder_id"],
        ["id"],
    )
    op.create_index("ix_palette_folder_id", "palette", ["folder_id"], unique=False)
    op.create_index(
        "uq_palette_user_folder_title",
        "palette",
        ["user_id", "folder_id", "title"],
        unique=True,
        postgresql_where=sa.text("folder_id IS NOT NULL"),
    )
    op.create_index(
        "uq_palette_user_root_title",
        "palette",
        ["user_id", "title"],
        unique=True,
        postgresql_where=sa.text("folder_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_palette_user_root_title", table_name="palette")
    op.drop_index("uq_palette_user_folder_title", table_name="palette")
    op.drop_index("ix_palette_folder_id", table_name="palette")
    op.drop_constraint("fk_palette_folder_id_folder", "palette", type_="foreignkey")
    op.drop_column("palette", "folder_id")

    op.drop_index("uq_folder_user_root_name", table_name="folder")
    op.drop_index("uq_folder_user_parent_name", table_name="folder")
    op.drop_index("ix_folder_name", table_name="folder")
    op.drop_index("ix_folder_parent_folder_id", table_name="folder")
    op.drop_index("ix_folder_user_id", table_name="folder")
    op.drop_table("folder")
