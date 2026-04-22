from sqlmodel import select

from app.models.user import User
from app.schemas.user import UserCreate, UserGetResponse
from app.core.database import SessionDep
from pwdlib import PasswordHash


class UserService:
    def create_user(userSchema: UserCreate, session: SessionDep):
        newUser = User(**userSchema.model_dump())

        hasher = PasswordHash.recommended()
        newUser.password = hasher.hash(newUser.password)

        session.add(newUser)
        session.commit()
        session.refresh(newUser)
        return newUser

    def get_user_from_username(username: str, session: SessionDep):
        query = select(User).where(User.username == username)
        user = session.exec(query).first()
        if user is None:
            return None
        return UserGetResponse(**user.model_dump())
