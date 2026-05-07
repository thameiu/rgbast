from sqlmodel import select, delete
from sqlalchemy import func
import difflib

from app.models.user import User
from app.models.folder import Folder
from app.models.palette import Palette
from app.schemas.user import UserCreate, UserGetResponse, UserUpdateMe
from app.core.database import SessionDep
from pwdlib import PasswordHash
from app.services.palette import PaletteService


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
        return UserGetResponse(
            id=user.id,
            username=user.username,
            firstname=user.firstname,
            lastname=user.lastname,
            birthdate=user.birthdate,
        )

    @staticmethod
    def get_user_model_by_username(username: str, session: SessionDep) -> User | None:
        return session.exec(select(User).where(User.username == username)).first()

    @staticmethod
    def get_user_model_by_email(email: str, session: SessionDep) -> User | None:
        return session.exec(
            select(User).where(func.lower(User.email) == email.strip().lower())
        ).first()

    @staticmethod
    def update_me(user_id: int, update_schema: UserUpdateMe, session: SessionDep) -> tuple[User, bool]:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("User not found.")

        username_changed = False

        if update_schema.username is not None:
            next_username = update_schema.username.strip()
            if not next_username:
                raise ValueError("Username cannot be empty.")
            if next_username != user.username:
                existing = session.exec(select(User).where(User.username == next_username)).first()
                if existing:
                    raise ValueError("This username is already taken.")
                user.username = next_username
                username_changed = True

        if update_schema.firstname is not None:
            user.firstname = update_schema.firstname.strip() or None
        if update_schema.lastname is not None:
            user.lastname = update_schema.lastname.strip() or None

        session.add(user)
        session.commit()
        session.refresh(user)
        return user, username_changed

    @staticmethod
    def delete_me(user_id: int, session: SessionDep) -> None:
        user = session.get(User, user_id)
        if not user:
            raise ValueError("User not found.")

        palette_ids = session.exec(
            select(Palette.id).where(Palette.user_id == user_id)
        ).all()
        for palette_id in palette_ids:
            PaletteService.delete_palette(palette_id, user_id, session)

        folder_ids = session.exec(select(Folder.id).where(Folder.user_id == user_id)).all()
        if folder_ids:
            session.exec(delete(Folder).where(Folder.id.in_(folder_ids)))

        session.delete(user)
        session.commit()

    def search_users(query: str, session: SessionDep, limit: int = 100):
        needle = query.strip().lower()
        if not needle:
            return []

        contains = f"%{needle}%"
        starts = f"{needle}%"
        candidate_limit = max(limit * 8, 240)
        users = session.exec(
            select(User)
            .where(
                User.username.ilike(contains)
                | User.firstname.ilike(contains)
                | User.lastname.ilike(contains)
            )
            .order_by(
                User.username.ilike(starts).desc(),
                User.firstname.ilike(starts).desc(),
                User.lastname.ilike(starts).desc(),
                User.username.asc(),
            )
            .limit(candidate_limit)
        ).all()
        scored: list[tuple[float, User]] = []
        for user in users:
            username = (user.username or "").lower()
            firstname = (user.firstname or "").lower()
            lastname = (user.lastname or "").lower()

            username_ratio = difflib.SequenceMatcher(None, needle, username).ratio()
            firstname_ratio = difflib.SequenceMatcher(None, needle, firstname).ratio() if firstname else 0.0
            lastname_ratio = difflib.SequenceMatcher(None, needle, lastname).ratio() if lastname else 0.0
            score = max(username_ratio, firstname_ratio * 0.95, lastname_ratio * 0.95)

            if needle in username:
                score += 0.35
            elif needle in firstname:
                score += 0.3
            elif needle in lastname:
                score += 0.3

            if username.startswith(needle):
                score += 0.2
            if firstname and firstname.startswith(needle):
                score += 0.15
            if lastname and lastname.startswith(needle):
                score += 0.15

            if score >= 0.26:
                scored.append((score, user))

        scored.sort(key=lambda item: (-item[0], item[1].username.lower()))
        top = scored[:limit]
        return [
            {
                "id": user.id,
                "username": user.username,
                "firstname": user.firstname,
                "lastname": user.lastname,
            }
            for _, user in top
        ]
