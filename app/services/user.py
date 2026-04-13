from app.models.user import User
from app.schemas.user import UserCreate
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
