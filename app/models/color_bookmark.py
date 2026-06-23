from datetime import datetime

from sqlalchemy import BigInteger, TIMESTAMP, UniqueConstraint, text
from sqlmodel import Field, SQLModel


class Color_Bookmark(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("user_id", "hex", name="uq_color_bookmark_user_hex"),
    )

    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    user_id: int = Field(
        index=True,
        default=None,
        foreign_key="user.id",
        nullable=False,
        sa_type=BigInteger(),
    )
    hex: str = Field(index=True, max_length=6, nullable=False)
    label: str = Field(max_length=100, nullable=False)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )
    updated_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "server_onupdate": text("CURRENT_TIMESTAMP"),
        },
        nullable=False,
    )
