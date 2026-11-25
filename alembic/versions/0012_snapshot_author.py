"""Record the username responsible for each new palette commit.

Historical authors cannot be reliably inferred; existing rows remain NULL.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("palette_snapshot", sa.Column("author", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("palette_snapshot", "author")
