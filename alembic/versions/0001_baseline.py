"""Baseline — initial schema as originally created by SQLModel.metadata.create_all

Revision ID: 0001
Revises:
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("firstname", sa.String(), nullable=True),
        sa.Column("lastname", sa.String(), nullable=True),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("birthdate", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    op.create_table(
        "palette",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_palette_title", "palette", ["title"])
    op.create_index("ix_palette_user_id", "palette", ["user_id"])

    op.create_table(
        "palette_branch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("palette_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("merged_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["palette_id"], ["palette.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_palette_branch_palette_id", "palette_branch", ["palette_id"])

    op.create_table(
        "palette_snapshot",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("palette_id", sa.Integer(), nullable=False),
        sa.Column("parent_snapshot_id", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["palette_branch.id"]),
        sa.ForeignKeyConstraint(["palette_id"], ["palette.id"]),
        sa.ForeignKeyConstraint(["parent_snapshot_id"], ["palette_snapshot.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_palette_snapshot_palette_id", "palette_snapshot", ["palette_id"])

    op.create_table(
        "palette_color",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("palette_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("hex", sa.String(length=6), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("position_key", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["palette_snapshot_id"], ["palette_snapshot.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_palette_color_palette_snapshot_id", "palette_color", ["palette_snapshot_id"])
    op.create_index("ix_palette_color_position_key", "palette_color", ["position_key"])

    op.create_table(
        "palette_change",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("previous_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("new_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("previous_color_id", sa.Integer(), nullable=True),
        sa.Column("new_color_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["new_color_id"], ["palette_color.id"]),
        sa.ForeignKeyConstraint(["new_snapshot_id"], ["palette_snapshot.id"]),
        sa.ForeignKeyConstraint(["previous_color_id"], ["palette_color.id"]),
        sa.ForeignKeyConstraint(["previous_snapshot_id"], ["palette_snapshot.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_palette_change_new_snapshot_id", "palette_change", ["new_snapshot_id"])
    op.create_index("ix_palette_change_previous_snapshot_id", "palette_change", ["previous_snapshot_id"])


def downgrade() -> None:
    op.drop_table("palette_change")
    op.drop_table("palette_color")
    op.drop_table("palette_snapshot")
    op.drop_table("palette_branch")
    op.drop_table("palette")
    op.drop_table("user")
