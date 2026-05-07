from fastapi import APIRouter, Depends

from app.controllers.colleague import ColleagueController
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.models.user import User
from app.schemas.colleague import (
    ColleagueActionResponse,
    ColleagueCountResponse,
    ColleagueDeleteResponse,
    ColleagueListResponse,
    ColleaguePublicListResponse,
    ColleagueStatusResponse,
)

router = APIRouter()


@router.get("/colleagues/me", response_model=ColleagueListResponse, status_code=200)
def list_my_colleagues_handler(
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColleagueController.list_me_control(current_user.id, session)


@router.post("/colleagues/{username}", response_model=ColleagueActionResponse, status_code=200)
def add_or_accept_colleague_handler(
    username: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColleagueController.add_or_accept_control(current_user.id, username, session)


@router.post("/colleagues/{username}/accept", response_model=ColleagueActionResponse, status_code=200)
def accept_colleague_handler(
    username: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColleagueController.accept_control(current_user.id, username, session)


@router.delete("/colleagues/{username}", response_model=ColleagueDeleteResponse, status_code=200)
def remove_colleague_handler(
    username: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColleagueController.delete_control(current_user.id, username, session)


@router.get("/colleagues/{username}/status", response_model=ColleagueStatusResponse, status_code=200)
def get_colleague_status_handler(
    username: str,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return ColleagueController.get_status_control(current_user.id, username, session)


@router.get("/users/{username}/colleagues/count", response_model=ColleagueCountResponse, status_code=200)
def get_colleague_count_by_username_handler(
    username: str,
    session: SessionDep,
):
    return ColleagueController.get_count_by_username_control(username, session)


@router.get("/users/{username}/colleagues", response_model=ColleaguePublicListResponse, status_code=200)
def list_public_colleagues_by_username_handler(
    username: str,
    session: SessionDep,
):
    return ColleagueController.list_public_by_username_control(username, session)
