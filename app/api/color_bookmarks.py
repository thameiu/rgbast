from fastapi import APIRouter, Depends

from app.controllers.color_bookmark import ColorBookmarkController
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.models.user import User
from app.schemas.color_bookmark import (
    ColorBookmarkByUsernameResponse,
    ColorBookmarkDeleteResponse,
    ColorBookmarkListResponse,
    ColorBookmarkResponse,
    ColorBookmarkUpsert,
)

router = APIRouter()


@router.get("/color-bookmarks", response_model=ColorBookmarkListResponse, status_code=200)
def list_my_color_bookmarks_handler(
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColorBookmarkController.list_mine_control(current_user.id, session)


@router.get("/color-bookmarks/{hex_value}", response_model=ColorBookmarkResponse, status_code=200)
def get_my_color_bookmark_handler(
    hex_value: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColorBookmarkController.get_mine_by_hex_control(current_user.id, hex_value, session)


@router.put("/color-bookmarks/{hex_value}", response_model=ColorBookmarkResponse, status_code=200)
def upsert_color_bookmark_handler(
    hex_value: str,
    payload: ColorBookmarkUpsert,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColorBookmarkController.upsert_control(current_user.id, hex_value, payload, session)


@router.delete("/color-bookmarks/{hex_value}", response_model=ColorBookmarkDeleteResponse, status_code=200)
def delete_color_bookmark_handler(
    hex_value: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColorBookmarkController.delete_control(current_user.id, hex_value, session)


@router.get(
    "/users/{username}/color-bookmarks",
    response_model=ColorBookmarkByUsernameResponse,
    status_code=200,
)
def list_color_bookmarks_by_username_handler(username: str, session: SessionDep):
    return ColorBookmarkController.list_by_username_control(username, session)
