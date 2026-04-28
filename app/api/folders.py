from fastapi import APIRouter, Depends

from app.controllers.folder import FolderController
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderCreateResponse, FolderResponse, FolderUpdate

router = APIRouter()


@router.get("/users/{username}/folders", response_model=list[FolderResponse], status_code=200)
def get_folders_by_username_handler(username: str, session: SessionDep):
    return FolderController.list_folders_by_username_control(username, session)


@router.post("/folders", response_model=FolderCreateResponse, status_code=201)
def create_folder_handler(
    folderSchema: FolderCreate,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return FolderController.create_folder_control(folderSchema, current_user.id, session)


@router.put("/folders/{folder_id}", response_model=FolderResponse, status_code=200)
def update_folder_handler(
    folder_id: int,
    folderSchema: FolderUpdate,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return FolderController.update_folder_control(
        folder_id, folderSchema, current_user.id, session
    )


@router.delete("/folders/{folder_id}", status_code=200)
def delete_folder_handler(
    folder_id: int,
    session: SessionDep,
    current_user: User = Depends(verify_token),
):
    return FolderController.delete_folder_control(folder_id, current_user.id, session)
