from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.database import SessionDep
from app.schemas.color_bookmark import (
    ColorBookmarkByUsernameResponse,
    ColorBookmarkDeleteResponse,
    ColorBookmarkListResponse,
    ColorBookmarkResponse,
    ColorBookmarkUpsert,
)
from app.services.color_bookmark import ColorBookmarkService


class ColorBookmarkController:
    @staticmethod
    def list_mine_control(user_id: int, session: SessionDep) -> ColorBookmarkListResponse:
        try:
            bookmarks = ColorBookmarkService.list_by_user_id(user_id, session)
            return ColorBookmarkListResponse(
                bookmarks=[ColorBookmarkResponse(**bookmark.model_dump()) for bookmark in bookmarks]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    @staticmethod
    def get_mine_by_hex_control(user_id: int, hex_value: str, session: SessionDep) -> ColorBookmarkResponse:
        try:
            bookmark = ColorBookmarkService.get_by_user_id_and_hex(user_id, hex_value, session)
            if not bookmark:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found.")
            return ColorBookmarkResponse(**bookmark.model_dump())
        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    @staticmethod
    def upsert_control(
        user_id: int,
        hex_value: str,
        payload: ColorBookmarkUpsert,
        session: SessionDep,
    ) -> ColorBookmarkResponse:
        try:
            bookmark = ColorBookmarkService.upsert(user_id, hex_value, payload, session)
            return ColorBookmarkResponse(**bookmark.model_dump())
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(e),
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    @staticmethod
    def delete_control(user_id: int, hex_value: str, session: SessionDep) -> ColorBookmarkDeleteResponse:
        try:
            normalized_hex = ColorBookmarkService.delete(user_id, hex_value, session)
            return ColorBookmarkDeleteResponse(hex=normalized_hex, deleted=True)
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )

    @staticmethod
    def list_by_username_control(username: str, session: SessionDep) -> ColorBookmarkByUsernameResponse:
        try:
            user, bookmarks = ColorBookmarkService.list_by_username(username, session)
            return ColorBookmarkByUsernameResponse(
                username=user.username,
                bookmarks=[ColorBookmarkResponse(**bookmark.model_dump()) for bookmark in bookmarks],
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred: " + str(e),
            )
