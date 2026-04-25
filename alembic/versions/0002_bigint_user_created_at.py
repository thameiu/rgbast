"""Migrate all integer PKs/FKs to BIGINT and add created_at to user

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables in FK-dependency order so referenced PKs are widened before their FKs.
_INT = sa.Integer()
_BIG = sa.BigInteger()


def upgrade() -> None:
    # ── user ─────────────────────────────────────────────────────────────────
    op.alter_column("user", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.add_column(
        "user",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # ── palette ───────────────────────────────────────────────────────────────
    op.alter_column("palette", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette", "user_id", existing_type=_INT, type_=_BIG, nullable=False)

    # ── palette_branch ────────────────────────────────────────────────────────
    op.alter_column("palette_branch", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_branch", "palette_id", existing_type=_INT, type_=_BIG, nullable=False)

    # ── palette_snapshot ──────────────────────────────────────────────────────
    op.alter_column("palette_snapshot", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_snapshot", "palette_id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_snapshot", "parent_snapshot_id", existing_type=_INT, type_=_BIG, nullable=True)
    op.alter_column("palette_snapshot", "branch_id", existing_type=_INT, type_=_BIG, nullable=True)

    # ── palette_color ─────────────────────────────────────────────────────────
    op.alter_column("palette_color", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_color", "palette_snapshot_id", existing_type=_INT, type_=_BIG, nullable=False)

    # ── palette_change ────────────────────────────────────────────────────────
    op.alter_column("palette_change", "id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_change", "previous_snapshot_id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_change", "new_snapshot_id", existing_type=_INT, type_=_BIG, nullable=False)
    op.alter_column("palette_change", "previous_color_id", existing_type=_INT, type_=_BIG, nullable=True)
    op.alter_column("palette_change", "new_color_id", existing_type=_INT, type_=_BIG, nullable=True)


def downgrade() -> None:
    op.alter_column("palette_change", "new_color_id", existing_type=_BIG, type_=_INT, nullable=True)
    op.alter_column("palette_change", "previous_color_id", existing_type=_BIG, type_=_INT, nullable=True)
    op.alter_column("palette_change", "new_snapshot_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette_change", "previous_snapshot_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette_change", "id", existing_type=_BIG, type_=_INT, nullable=False)

    op.alter_column("palette_color", "palette_snapshot_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette_color", "id", existing_type=_BIG, type_=_INT, nullable=False)

    op.alter_column("palette_snapshot", "branch_id", existing_type=_BIG, type_=_INT, nullable=True)
    op.alter_column("palette_snapshot", "parent_snapshot_id", existing_type=_BIG, type_=_INT, nullable=True)
    op.alter_column("palette_snapshot", "palette_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette_snapshot", "id", existing_type=_BIG, type_=_INT, nullable=False)

    op.alter_column("palette_branch", "palette_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette_branch", "id", existing_type=_BIG, type_=_INT, nullable=False)

    op.alter_column("palette", "user_id", existing_type=_BIG, type_=_INT, nullable=False)
    op.alter_column("palette", "id", existing_type=_BIG, type_=_INT, nullable=False)

    op.drop_column("user", "created_at")
    op.alter_column("user", "id", existing_type=_BIG, type_=_INT, nullable=False)
