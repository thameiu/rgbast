"""Add color_bookmark table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("color_bookmark"):
        op.create_table(
            "color_bookmark",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("hex", sa.String(length=6), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.UniqueConstraint("user_id", "hex", name="uq_color_bookmark_user_hex"),
        )
    else:
        columns = {column["name"] for column in inspector.get_columns("color_bookmark")}
        if "updated_at" not in columns:
            op.add_column(
                "color_bookmark",
                sa.Column(
                    "updated_at",
                    sa.TIMESTAMP(timezone=True),
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                    nullable=False,
                ),
            )

    indexes = {index["name"] for index in inspector.get_indexes("color_bookmark")}
    if "ix_color_bookmark_user_id" not in indexes:
        op.create_index("ix_color_bookmark_user_id", "color_bookmark", ["user_id"])
    if "ix_color_bookmark_hex" not in indexes:
        op.create_index("ix_color_bookmark_hex", "color_bookmark", ["hex"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("color_bookmark"):
        return

    indexes = {index["name"] for index in inspector.get_indexes("color_bookmark")}
    if "ix_color_bookmark_hex" in indexes:
        op.drop_index("ix_color_bookmark_hex", table_name="color_bookmark")
    if "ix_color_bookmark_user_id" in indexes:
        op.drop_index("ix_color_bookmark_user_id", table_name="color_bookmark")
    op.drop_table("color_bookmark")
