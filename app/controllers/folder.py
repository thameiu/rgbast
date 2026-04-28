from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.database import SessionDep
from app.schemas.folder import FolderCreate, FolderCreateResponse, FolderResponse, FolderUpdate
from app.services.folder import FolderService


class FolderController:
    def list_folders_by_username_control(
        username: str, session: SessionDep
    ) -> list[FolderResponse]:
        try:
            folders = FolderService.list_folders_by_username(username, session)
            return [FolderResponse(**f.model_dump()) for f in folders]
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    def create_folder_control(
        folderSchema: FolderCreate, user_id: int, session: SessionDep
    ) -> FolderCreateResponse:
        try:
            folder = FolderService.create_folder(folderSchema, user_id, session)
            return FolderCreateResponse(**folder.model_dump())
        except PermissionError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    def update_folder_control(
        folder_id: int,
        folderSchema: FolderUpdate,
        user_id: int,
        session: SessionDep,
    ) -> FolderResponse:
        try:
            folder = FolderService.update_folder(folder_id, folderSchema, user_id, session)
            return FolderResponse(**folder.model_dump())
        except PermissionError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    def delete_folder_control(
        folder_id: int,
        user_id: int,
        session: SessionDep,
    ) -> dict:
        try:
            FolderService.delete_folder(folder_id, user_id, session)
            return {"folder_id": folder_id}
        except PermissionError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        except ValueError as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
