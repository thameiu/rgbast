from sqlmodel import SQLModel


class Login(SQLModel):
    username: str | None
    password: str


class LoginResponse(SQLModel):
    access_token: str
    username: str
    firstname: str | None
    lastname: str | None
    email: str
