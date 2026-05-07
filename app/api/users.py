from fastapi import APIRouter
from app.controllers.user import UserController
from app.core.database import SessionDep
from app.schemas.user import UserCreate, UserCreateResponse, UserGetResponse

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
