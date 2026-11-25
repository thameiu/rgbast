"""Allow independent bookmarks of identical colors, including in projects."""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_color_bookmark_user_hex", "color_bookmark", type_="unique")
    op.add_column("color_bookmark", sa.Column("project_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key("fk_bookmark_project", "color_bookmark", "project", ["project_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_color_bookmark_project_id", "color_bookmark", ["project_id"])


def downgrade():
    # Never silently delete duplicate bookmarks to recreate the old uniqueness.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM color_bookmark GROUP BY user_id, hex HAVING count(*) > 1 LIMIT 1")).first():
        raise RuntimeError("Resolve duplicate bookmarks before downgrading; no bookmarks were deleted.")
    if bind.execute(sa.text("SELECT 1 FROM color_bookmark WHERE project_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Move project bookmarks to personal space before downgrading.")
    op.drop_index("ix_color_bookmark_project_id", table_name="color_bookmark")
    op.drop_constraint("fk_bookmark_project", "color_bookmark", type_="foreignkey")
    op.drop_column("color_bookmark", "project_id")
    op.create_unique_constraint("uq_color_bookmark_user_hex", "color_bookmark", ["user_id", "hex"])
