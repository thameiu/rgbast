from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, JSON, Text, TIMESTAMP, UniqueConstraint
from sqlmodel import Field, SQLModel

PERMISSIONS = (
    "read", "add_palettes", "edit_palettes", "remove_palettes", "add_bookmarks",
    "edit_bookmarks", "remove_bookmarks", "manage_folders", "manage_access", "edit_project",
)


class Project(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("creator_id", "slug", name="uq_project_creator_slug"),)
    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    title: str = Field(max_length=50)
    slug: str = Field(max_length=50)
    description: str | None = Field(default=None, sa_type=Text)
    creator_id: int = Field(foreign_key="user.id", sa_type=BigInteger, index=True)
    private: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))


class ProjectAccess(SQLModel, table=True):
    __tablename__ = "project_access"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", "permission", name="uq_project_access"),
        CheckConstraint("permission IN (" + ",".join(repr(p) for p in PERMISSIONS) + ")", name="ck_project_permission"),
    )
    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE", sa_type=BigInteger, index=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE", sa_type=BigInteger, index=True)
    permission: str = Field(max_length=32)
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))


class ProjectInvitation(SQLModel, table=True):
    __tablename__ = "project_invitation"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_invitation"),)
    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    project_id: int = Field(foreign_key="project.id", ondelete="CASCADE", sa_type=BigInteger, index=True)
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE", sa_type=BigInteger, index=True)
    inviter_id: int = Field(foreign_key="user.id", ondelete="CASCADE", sa_type=BigInteger)
    permissions: list[str] = Field(default_factory=list, sa_type=JSON)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_type=TIMESTAMP(timezone=True))
