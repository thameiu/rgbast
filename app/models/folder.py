from datetime import datetime

from sqlalchemy import BigInteger
from sqlmodel import Field, SQLModel, TIMESTAMP, text


class Folder(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    user_id: int = Field(
        index=True,
        default=None,
        foreign_key="user.id",
        nullable=False,
        sa_type=BigInteger(),
    )
    parent_folder_id: int | None = Field(
        index=True,
        default=None,
        foreign_key="folder.id",
        nullable=True,
        sa_type=BigInteger(),
    )
    name: str = Field(index=True, max_length=50, nullable=False)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )
