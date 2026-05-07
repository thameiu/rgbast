"""Add email verification fields on user

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "email_verified_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.execute('UPDATE "user" SET is_email_verified = true, email_verified_at = CURRENT_TIMESTAMP')
    op.alter_column("user", "is_email_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("user", "email_verified_at")
    op.drop_column("user", "is_email_verified")
