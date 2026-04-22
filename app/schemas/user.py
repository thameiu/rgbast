from datetime import datetime
from sqlmodel import Field, SQLModel
from pydantic import EmailStr, field_validator
import re


class UserUtils:
    def validate_password(password: str):
        pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[#?!@$%^&*\-.]).{8,255}$"
        return re.match(pattern, password)


class UserCreate(SQLModel):
    username: str = Field(max_length=50)
    email: EmailStr
    firstname: str | None = Field(default=None, max_length=50)
    lastname: str | None = Field(default=None, max_length=50)
    password: str
    birthdate: datetime | None

    @field_validator("username")
    @classmethod
    def validate_username_user_create(cls, username: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, username):
            raise ValueError("Username is invalid.")
        return username

    @field_validator("password")
    @classmethod
    def validate_password_user_create(cls, password: str) -> str:
        if not UserUtils.validate_password(password):
            raise ValueError("Password is too weak.")
        return password


class UserCreateResponse(SQLModel):
    response: str
    username: str
    email: EmailStr
    firstname: str | None
    lastname: str | None
    birthdate: datetime | None = None


class UserGetResponse(SQLModel):
    id: int
    username: str
    email: str
    firstname: str | None
    lastname: str | None
    birthdate: datetime | None = None
