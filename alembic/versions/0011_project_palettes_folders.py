"""Separate personal and project palette/folder namespaces."""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("folder", "palette"):
        op.add_column(table, sa.Column("project_id", sa.BigInteger(), nullable=True))
        op.create_foreign_key(f"fk_{table}_project", table, "project", ["project_id"], ["id"])
        op.create_index(f"ix_{table}_project_id", table, ["project_id"])
    for table, parent, value, nested, root in (
        ("folder", "parent_folder_id", "name", "uq_folder_user_parent_name", "uq_folder_user_root_name"),
        ("palette", "folder_id", "title", "uq_palette_user_folder_title", "uq_palette_user_root_title"),
    ):
        op.drop_index(nested, table_name=table)
        op.drop_index(root, table_name=table)
        op.create_index(nested, table, ["user_id", parent, value], unique=True,
                        postgresql_where=sa.text(f"project_id IS NULL AND {parent} IS NOT NULL"))
        op.create_index(root, table, ["user_id", value], unique=True,
                        postgresql_where=sa.text(f"project_id IS NULL AND {parent} IS NULL"))
        op.create_index(f"uq_{table}_project_nested", table, ["project_id", parent, value], unique=True,
                        postgresql_where=sa.text(f"project_id IS NOT NULL AND {parent} IS NOT NULL"))
        op.create_index(f"uq_{table}_project_root", table, ["project_id", value], unique=True,
                        postgresql_where=sa.text(f"project_id IS NOT NULL AND {parent} IS NULL"))


def downgrade():
    bind = op.get_bind()
    if any(bind.execute(sa.text(f"SELECT 1 FROM {table} WHERE project_id IS NOT NULL LIMIT 1")).first()
           for table in ("folder", "palette")):
        raise RuntimeError("Remove project content before downgrading; no data was deleted.")
    for table, parent, value, nested, root in (
        ("folder", "parent_folder_id", "name", "uq_folder_user_parent_name", "uq_folder_user_root_name"),
        ("palette", "folder_id", "title", "uq_palette_user_folder_title", "uq_palette_user_root_title"),
    ):
        for index in (nested, root, f"uq_{table}_project_nested", f"uq_{table}_project_root"):
            op.drop_index(index, table_name=table)
        op.create_index(nested, table, ["user_id", parent, value], unique=True,
                        postgresql_where=sa.text(f"{parent} IS NOT NULL"))
        op.create_index(root, table, ["user_id", value], unique=True,
                        postgresql_where=sa.text(f"{parent} IS NULL"))
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_constraint(f"fk_{table}_project", table, type_="foreignkey")
        op.drop_column(table, "project_id")
