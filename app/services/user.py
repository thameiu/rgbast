from sqlmodel import select
import difflib

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
        return UserGetResponse(
            id=user.id,
            username=user.username,
            firstname=user.firstname,
            lastname=user.lastname,
            birthdate=user.birthdate,
        )

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
