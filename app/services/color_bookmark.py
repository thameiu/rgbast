from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import desc, select

from app.models.color_bookmark import Color_Bookmark
from app.models.user import User
from app.services.color import ColorService
from app.services.project import ProjectService


class ColorBookmarkService:
    @staticmethod
    def list_by_user_id(user_id, session, hex_value=None, project_id=None):
        query = select(Color_Bookmark)
        if project_id is not None:
            ProjectService.require(project_id, user_id, session)
            query = query.where(Color_Bookmark.project_id == project_id)
        else:
            query = query.where(Color_Bookmark.user_id == user_id, Color_Bookmark.project_id.is_(None))
        if hex_value is not None:
            try:
                hex_value = ColorService._normalize_hex(hex_value)
            except ValueError as error:
                raise HTTPException(422, str(error))
            query = query.where(Color_Bookmark.hex == hex_value)
        return list(session.exec(query.order_by(desc(Color_Bookmark.created_at), desc(Color_Bookmark.id))).all())

    @staticmethod
    def get(bookmark_id, user_id, session, permission='read'):
        bookmark = session.get(Color_Bookmark, bookmark_id)
        if not bookmark:
            raise HTTPException(404, 'Bookmark not found.')
        if bookmark.project_id is not None:
            ProjectService.require(bookmark.project_id, user_id, session, permission)
        elif bookmark.user_id != user_id:
            raise HTTPException(404, 'Bookmark not found.')
        return bookmark

    @staticmethod
    def create(user_id, payload, session):
        if payload.project_id is not None:
            ProjectService.require(payload.project_id, user_id, session, 'add_bookmarks', lock=True)
        bookmark = Color_Bookmark(user_id=user_id, hex=payload.hex, label=payload.label,
                                  project_id=payload.project_id)
        session.add(bookmark)
        session.commit()
        session.refresh(bookmark)
        return bookmark

    @staticmethod
    def update(user_id, bookmark_id, payload, session):
        bookmark = ColorBookmarkService.get(bookmark_id, user_id, session, 'edit_bookmarks')
        if bookmark.project_id is not None:
            ProjectService.require(bookmark.project_id, user_id, session, 'edit_bookmarks', lock=True)
        bookmark.label = payload.label
        bookmark.updated_at = datetime.now(timezone.utc)
        session.add(bookmark)
        session.commit()
        session.refresh(bookmark)
        return bookmark

    @staticmethod
    def delete(user_id, bookmark_id, session):
        bookmark = ColorBookmarkService.get(bookmark_id, user_id, session, 'remove_bookmarks')
        if bookmark.project_id is not None:
            ProjectService.require(bookmark.project_id, user_id, session, 'remove_bookmarks', lock=True)
        result = {'id': bookmark.id, 'hex': bookmark.hex, 'deleted': True}
        session.delete(bookmark)
        session.commit()
        return result

    @staticmethod
    def list_by_username(username, session):
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(404, 'User not found.')
        return user, ColorBookmarkService.list_by_user_id(user.id, session)
