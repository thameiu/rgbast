from app.schemas.color_bookmark import ColorBookmarkByUsernameResponse, ColorBookmarkListResponse
from app.services.color_bookmark import ColorBookmarkService


class ColorBookmarkController:
    @staticmethod
    def list_mine_control(user_id, session, hex_value=None, project_id=None):
        return ColorBookmarkListResponse(bookmarks=ColorBookmarkService.list_by_user_id(
            user_id, session, hex_value, project_id))

    @staticmethod
    def list_by_username_control(username, session):
        user, bookmarks = ColorBookmarkService.list_by_username(username, session)
        return ColorBookmarkByUsernameResponse(username=user.username, bookmarks=bookmarks)
