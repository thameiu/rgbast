from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
import jwt
from sqlmodel import select

from app.models.user import User
from app.schemas.auth import Login, LoginResponse
from app.core.database import SessionDep
from pwdlib import PasswordHash

from app.services.user import UserService

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 60


class AuthService:
    def login(loginSchema: Login, session: SessionDep) -> LoginResponse:
        hasher = PasswordHash.recommended()
        if "@" in loginSchema.username:
            query = select(User).where(User.email == loginSchema.username)
        else:
            query = select(User).where(User.username == loginSchema.username)

        # Team tout à la fois ou vérifications séparées ? A vos claviers !
        result = session.exec(query).first()
        if result and hasher.verify(loginSchema.password, result.password):
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_DAYS)
            token = AuthService.create_access_token(
                data={"sub": result.username},
                expires_delta=access_token_expires,
            )
            return LoginResponse(
                access_token=token,
                username=result.username,
                firstname=result.firstname,
                lastname=result.lastname,
                email=result.email,
            )
        return None

    def check_auth(token: str, session: SessionDep):
        load_dotenv()

        secret_key = os.getenv("SECRET_KEY", "key_and_peele")
        decoded_token = jwt.decode(jwt=token, key=secret_key, algorithms=[ALGORITHM])
        return UserService.get_user_from_username(decoded_token.get("sub"), session)

    def create_access_token(data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else timedelta(days=60)
        )
        to_encode.update({"exp": expire})

        load_dotenv()
        secret_key = os.getenv("SECRET_KEY", "key_and_peele")
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
        return encoded_jwt
