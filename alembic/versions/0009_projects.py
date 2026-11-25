"""Projects, normalized permissions and pending invitations."""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("project",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.String(50), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("creator_id", sa.BigInteger(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("private", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("creator_id", "slug", name="uq_project_creator_slug"))
    op.create_table("project_access",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", "permission", name="uq_project_access"),
        sa.CheckConstraint("permission IN ('read','add_palettes','edit_palettes','remove_palettes','add_bookmarks','edit_bookmarks','remove_bookmarks','manage_folders','manage_access','edit_project')", name="ck_project_permission"))
    op.create_table("project_invitation",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inviter_id", sa.BigInteger(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_invitation"))
    op.create_index("ix_project_creator_id", "project", ["creator_id"])
    for table in ("project_access", "project_invitation"):
        for column in ("project_id", "user_id"):
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    op.drop_table("project_invitation")
    op.drop_table("project_access")
    op.drop_table("project")
