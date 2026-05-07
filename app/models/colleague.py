from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, TIMESTAMP, UniqueConstraint, text
from sqlmodel import Field, SQLModel


class Colleague(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_colleague_from_to"),
        CheckConstraint("status IN ('pending','accepted')", name="ck_colleague_status"),
    )

    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    from_user_id: int = Field(
        index=True,
        default=None,
        foreign_key="user.id",
        nullable=False,
        sa_type=BigInteger(),
    )
    to_user_id: int = Field(
        index=True,
        default=None,
        foreign_key="user.id",
        nullable=False,
        sa_type=BigInteger(),
    )
    status: str = Field(default="pending", max_length=16, nullable=False)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )
    accepted_at: datetime | None = Field(
        sa_type=TIMESTAMP(timezone=True),
        default=None,
        nullable=True,
    )
