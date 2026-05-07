"""Add colleagues table

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "colleague",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("from_user_id", sa.BigInteger(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("to_user_id", sa.BigInteger(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending','accepted')", name="ck_colleague_status"),
        sa.UniqueConstraint("from_user_id", "to_user_id", name="uq_colleague_from_to"),
    )
    op.create_index("ix_colleague_from_user_id", "colleague", ["from_user_id"], unique=False)
    op.create_index("ix_colleague_to_user_id", "colleague", ["to_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_colleague_to_user_id", table_name="colleague")
    op.drop_index("ix_colleague_from_user_id", table_name="colleague")
    op.drop_table("colleague")
