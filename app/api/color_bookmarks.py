from fastapi import APIRouter, Depends, HTTPException

from app.controllers.color_bookmark import ColorBookmarkController
from app.core.database import SessionDep
from app.middlewares.auth import optional_user, verify_token
from app.schemas.color_bookmark import (
    ColorBookmarkByUsernameResponse, ColorBookmarkCreate, ColorBookmarkDeleteResponse,
    ColorBookmarkListResponse, ColorBookmarkResponse, ColorBookmarkUpsert,
)
from app.services.color_bookmark import ColorBookmarkService

router = APIRouter()


@router.get('/color-bookmarks', response_model=ColorBookmarkListResponse)
def list_bookmarks(session: SessionDep, hex: str | None = None, project_id: int | None = None,
                   user=Depends(optional_user)):
    if project_id is None and user is None:
        raise HTTPException(401, 'Authentication required.')
    return ColorBookmarkController.list_mine_control(user.id if user else None, session, hex, project_id)


@router.post('/color-bookmarks', response_model=ColorBookmarkResponse, status_code=201)
def create_bookmark(payload: ColorBookmarkCreate, session: SessionDep, user=Depends(verify_token)):
    return ColorBookmarkService.create(user.id, payload, session)


# Separate id paths prevent old clients from treating numeric hex codes as ids.
@router.get('/color-bookmarks/by-id/{bookmark_id}', response_model=ColorBookmarkResponse)
def get_bookmark(bookmark_id: int, session: SessionDep, user=Depends(verify_token)):
    return ColorBookmarkService.get(bookmark_id, user.id, session)


@router.patch('/color-bookmarks/by-id/{bookmark_id}', response_model=ColorBookmarkResponse)
def update_bookmark(bookmark_id: int, payload: ColorBookmarkUpsert, session: SessionDep,
                    user=Depends(verify_token)):
    return ColorBookmarkService.update(user.id, bookmark_id, payload, session)


@router.delete('/color-bookmarks/by-id/{bookmark_id}', response_model=ColorBookmarkDeleteResponse)
def delete_bookmark(bookmark_id: int, session: SessionDep, user=Depends(verify_token)):
    return ColorBookmarkService.delete(user.id, bookmark_id, session)


@router.get('/users/{username}/color-bookmarks', response_model=ColorBookmarkByUsernameResponse)
def public_bookmarks(username: str, session: SessionDep):
    return ColorBookmarkController.list_by_username_control(username, session)
