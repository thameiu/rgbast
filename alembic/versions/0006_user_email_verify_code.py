"""Add email verification code fields on user

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("email_verify_code_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("email_verify_code_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "email_verify_code_expires_at")
    op.drop_column("user", "email_verify_code_hash")
