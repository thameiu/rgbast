from sqlmodel import SQLModel
from pydantic import EmailStr


class Login(SQLModel):
    username: str
    password: str


class LoginResponse(SQLModel):
    access_token: str
    username: str
    firstname: str | None
    lastname: str | None
    email: str


class PasswordResetRequest(SQLModel):
    email: EmailStr


class PasswordResetConfirm(SQLModel):
    token: str
    password: str


class MessageResponse(SQLModel):
    response: str
