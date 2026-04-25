from sqlalchemy import BigInteger, TIMESTAMP, text
from sqlmodel import Field, SQLModel
from datetime import datetime


class User(SQLModel, table=True):
    id: int = Field(primary_key=True, sa_type=BigInteger(), nullable=False)
    username: str = Field(default=None, index=True, unique=True, nullable=False)
    email: str = Field(default=None, index=True, unique=True, nullable=False)
    firstname: str | None = Field(default=None, nullable=True)
    lastname: str | None = Field(default=None, nullable=True)
    password: str = Field(default=None)
    birthdate: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")},
        nullable=False,
    )
