from sqlmodel import Field, SQLModel
from datetime import datetime


class User(SQLModel, table=True):
    id: int = Field(primary_key=True, nullable=False)
    username: str = Field(default=None, index=True, unique=True, nullable=False)
    email: str = Field(default=None, index=True, unique=True, nullable=False)
    firstname: str | None = Field(default=None)
    lastname: str | None = Field(default=None, max_length=50)
    password: str = Field(default=None)
    birthdate: datetime = Field(default=None)
    # birthdate: datetime = Field(sa_column=Column(DateTime(timezone=True),nullable=True))
