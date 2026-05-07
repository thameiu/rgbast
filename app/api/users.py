from fastapi import APIRouter, Depends
from app.controllers.user import UserController
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.schemas.user import (
    UserCreate,
    UserCreateResponse,
    UserDeleteMeResponse,
    UserGetResponse,
    UserUpdateMe,
    UserUpdateMeResponse,
)

router = APIRouter()


@router.post("/users", response_model=UserCreateResponse, status_code=201)
def create_user_handler(user: UserCreate, session: SessionDep):
    return UserController.create_user_control(user, session)


@router.get("/users", response_model=UserGetResponse, status_code=200)
def get_user_from_username_handler(username: str, session: SessionDep):
    return UserController.get_user_from_username_control(username, session)


@router.get("/users/{username}", response_model=UserGetResponse, status_code=200)
def get_user_by_username_handler(username: str, session: SessionDep):
    return UserController.get_user_or_404_control(username, session)


@router.patch("/users/me", response_model=UserUpdateMeResponse, status_code=200)
def update_me_handler(
    payload: UserUpdateMe,
    session: SessionDep,
    current_user=Depends(verify_token),
):
    return UserController.update_me_control(current_user.id, payload, session)


@router.delete("/users/me", response_model=UserDeleteMeResponse, status_code=200)
def delete_me_handler(session: SessionDep, current_user=Depends(verify_token)):
    return UserController.delete_me_control(current_user.id, session)
