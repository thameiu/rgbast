from datetime import datetime, timezone

from sqlmodel import desc, select

from app.core.database import SessionDep
from app.models.color_bookmark import Color_Bookmark
from app.models.user import User
from app.schemas.color_bookmark import ColorBookmarkUpsert
from app.services.color import ColorService


class ColorBookmarkService:
    @staticmethod
    def list_by_user_id(user_id: int, session: SessionDep) -> list[Color_Bookmark]:
        return list(
            session.exec(
                select(Color_Bookmark)
                .where(Color_Bookmark.user_id == user_id)
                .order_by(desc(Color_Bookmark.created_at), desc(Color_Bookmark.id))
            ).all()
        )

    @staticmethod
    def get_by_user_id_and_hex(user_id: int, hex_value: str, session: SessionDep) -> Color_Bookmark | None:
        normalized_hex = ColorService._normalize_hex(hex_value)
        return session.exec(
            select(Color_Bookmark).where(
                Color_Bookmark.user_id == user_id,
                Color_Bookmark.hex == normalized_hex,
            )
        ).first()

    @staticmethod
    def upsert(user_id: int, hex_value: str, payload: ColorBookmarkUpsert, session: SessionDep) -> Color_Bookmark:
        normalized_hex = ColorService._normalize_hex(hex_value)
        bookmark = ColorBookmarkService.get_by_user_id_and_hex(user_id, normalized_hex, session)
        if bookmark:
            bookmark.label = payload.label.strip()
            bookmark.updated_at = datetime.now(timezone.utc)
        else:
            bookmark = Color_Bookmark(
                user_id=user_id,
                hex=normalized_hex,
                label=payload.label.strip(),
            )
            session.add(bookmark)
        session.commit()
        session.refresh(bookmark)
        return bookmark

    @staticmethod
    def delete(user_id: int, hex_value: str, session: SessionDep) -> str:
        bookmark = ColorBookmarkService.get_by_user_id_and_hex(user_id, hex_value, session)
        if not bookmark:
            raise ValueError("Bookmark not found.")
        normalized_hex = bookmark.hex
        session.delete(bookmark)
        session.commit()
        return normalized_hex

    @staticmethod
    def list_by_username(username: str, session: SessionDep) -> tuple[User, list[Color_Bookmark]]:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found.")
        bookmarks = ColorBookmarkService.list_by_user_id(user.id, session)
        return user, bookmarks
