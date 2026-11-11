"""Add and backfill user profile colors.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("profile_color", sa.String(6), nullable=True))
    op.execute('UPDATE "user" SET profile_color = upper(substr(md5(random()::text || id::text), 1, 6))')
    op.alter_column("user", "profile_color", existing_type=sa.String(6), nullable=False)
    op.create_check_constraint("ck_user_profile_color_hex", "user", "profile_color ~ '^[0-9A-F]{6}$'")


def downgrade() -> None:
    op.drop_constraint("ck_user_profile_color_hex", "user", type_="check")
    op.drop_column("user", "profile_color")
