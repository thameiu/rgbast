from sqlmodel import select

from app.core.database import SessionDep
from app.models.folder import Folder
from app.models.palette import Palette
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate


class FolderService:
    @staticmethod
    def _get_user_by_username(username: str, session: SessionDep) -> User:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found.")
        return user

    @staticmethod
    def _assert_folder_owner(folder_id: int, user_id: int, session: SessionDep) -> Folder:
        folder = session.get(Folder, folder_id)
        if not folder:
            raise ValueError("Folder not found.")
        if folder.user_id != user_id:
            raise PermissionError("You do not have permission to modify this folder.")
        return folder

    @staticmethod
    def _assert_unique_name(
        user_id: int,
        parent_folder_id: int | None,
        name: str,
        session: SessionDep,
        ignore_folder_id: int | None = None,
    ) -> None:
        query = select(Folder).where(
            Folder.user_id == user_id,
            Folder.name == name,
        )
        if parent_folder_id is None:
            query = query.where(Folder.parent_folder_id.is_(None))
        else:
            query = query.where(Folder.parent_folder_id == parent_folder_id)
        if ignore_folder_id is not None:
            query = query.where(Folder.id != ignore_folder_id)
        if session.exec(query).first():
            raise ValueError("Folder name already exists in this parent.")

    @staticmethod
    def _assert_parent_valid(
        user_id: int,
        folder_id: int,
        parent_folder_id: int | None,
        session: SessionDep,
    ) -> None:
        if parent_folder_id is None:
            return
        if parent_folder_id == folder_id:
            raise ValueError("Folder cannot be its own parent.")
        parent = session.get(Folder, parent_folder_id)
        if not parent:
            raise ValueError("Parent folder not found.")
        if parent.user_id != user_id:
            raise PermissionError("You do not have permission to use this parent folder.")

        # Detect cycles by walking up the tree.
        current = parent
        seen: set[int] = set()
        while current:
            if current.id in seen:
                break
            if current.id == folder_id:
                raise ValueError("Folder cannot be moved into its own child.")
            seen.add(current.id)
            if current.parent_folder_id is None:
                break
            current = session.get(Folder, current.parent_folder_id)

    @staticmethod
    def list_folders_by_username(username: str, session: SessionDep) -> list[Folder]:
        user = FolderService._get_user_by_username(username, session)
        return session.exec(
            select(Folder)
            .where(Folder.user_id == user.id)
            .order_by(Folder.parent_folder_id.is_(None).desc(), Folder.name)
        ).all()

    @staticmethod
    def create_folder(
        folderSchema: FolderCreate,
        user_id: int,
        session: SessionDep,
    ) -> Folder:
        FolderService._assert_unique_name(
            user_id, folderSchema.parent_folder_id, folderSchema.name, session
        )
        if folderSchema.parent_folder_id is not None:
            parent = session.get(Folder, folderSchema.parent_folder_id)
            if not parent:
                raise ValueError("Parent folder not found.")
            if parent.user_id != user_id:
                raise PermissionError("You do not have permission to use this parent folder.")

        folder = Folder(
            user_id=user_id,
            parent_folder_id=folderSchema.parent_folder_id,
            name=folderSchema.name,
        )
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def update_folder(
        folder_id: int,
        folderSchema: FolderUpdate,
        user_id: int,
        session: SessionDep,
    ) -> Folder:
        folder = FolderService._assert_folder_owner(folder_id, user_id, session)

        next_name = folderSchema.name if folderSchema.name is not None else folder.name
        next_parent = (
            folderSchema.parent_folder_id
            if folderSchema.parent_folder_id is not None
            else folder.parent_folder_id
        )

        FolderService._assert_parent_valid(user_id, folder.id, next_parent, session)
        FolderService._assert_unique_name(user_id, next_parent, next_name, session, ignore_folder_id=folder.id)

        folder.name = next_name
        folder.parent_folder_id = next_parent
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def delete_folder(folder_id: int, user_id: int, session: SessionDep) -> None:
        folder = FolderService._assert_folder_owner(folder_id, user_id, session)

        has_children = session.exec(
            select(Folder.id).where(Folder.parent_folder_id == folder_id)
        ).first()
        if has_children:
            raise ValueError("Folder has subfolders.")

        has_palettes = session.exec(
            select(Palette.id).where(Palette.folder_id == folder_id)
        ).first()
        if has_palettes:
            raise ValueError("Folder contains palettes.")

        session.delete(folder)
        session.commit()
from sqlmodel import select

from app.core.database import SessionDep
from app.models.folder import Folder
from app.models.palette import Palette
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate


class FolderService:
    @staticmethod
    def _get_user_by_username(username: str, session: SessionDep) -> User:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise ValueError("User not found.")
        return user

    @staticmethod
    def _assert_folder_owner(folder_id: int, user_id: int, session: SessionDep) -> Folder:
        folder = session.get(Folder, folder_id)
        if not folder:
            raise ValueError("Folder not found.")
        if folder.user_id != user_id:
            raise PermissionError("You do not have permission to use this folder.")
        return folder

    @staticmethod
    def _assert_folder_unique(
        user_id: int,
        parent_folder_id: int | None,
        name: str,
        session: SessionDep,
        ignore_folder_id: int | None = None,
    ) -> None:
        query = select(Folder).where(
            Folder.user_id == user_id,
            Folder.name == name,
        )
        if parent_folder_id is None:
            query = query.where(Folder.parent_folder_id.is_(None))
        else:
            query = query.where(Folder.parent_folder_id == parent_folder_id)
        if ignore_folder_id is not None:
            query = query.where(Folder.id != ignore_folder_id)
        if session.exec(query).first():
            raise ValueError("Folder name already exists in this parent.")

    @staticmethod
    def _assert_parent_valid(
        folder_id: int,
        parent_folder_id: int | None,
        session: SessionDep,
    ) -> None:
        if parent_folder_id is None:
            return
        if parent_folder_id == folder_id:
            raise ValueError("Folder cannot be its own parent.")
        seen: set[int] = set()
        current_id: int | None = parent_folder_id
        while current_id is not None:
            if current_id in seen:
                raise ValueError("Folder hierarchy is invalid.")
            if current_id == folder_id:
                raise ValueError("Folder cannot be moved into its child.")
            seen.add(current_id)
            folder = session.get(Folder, current_id)
            if not folder:
                raise ValueError("Parent folder not found.")
            current_id = folder.parent_folder_id

    @staticmethod
    def list_folders_by_username(username: str, session: SessionDep):
        user = FolderService._get_user_by_username(username, session)
        folders = session.exec(
            select(Folder).where(Folder.user_id == user.id).order_by(Folder.name)
        ).all()
        return folders

    @staticmethod
    def create_folder(folder_schema: FolderCreate, user_id: int, session: SessionDep) -> Folder:
        if folder_schema.parent_folder_id is not None:
            parent = session.get(Folder, folder_schema.parent_folder_id)
            if not parent:
                raise ValueError("Parent folder not found.")
            if parent.user_id != user_id:
                raise PermissionError("You do not have permission to use this folder.")

        FolderService._assert_folder_unique(
            user_id, folder_schema.parent_folder_id, folder_schema.name, session
        )

        folder = Folder(
            user_id=user_id,
            parent_folder_id=folder_schema.parent_folder_id,
            name=folder_schema.name,
        )
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def update_folder(
        folder_id: int,
        folder_schema: FolderUpdate,
        user_id: int,
        session: SessionDep,
    ) -> Folder:
        folder = FolderService._assert_folder_owner(folder_id, user_id, session)

        next_name = folder_schema.name if folder_schema.name is not None else folder.name
        next_parent_id = (
            folder_schema.parent_folder_id
            if folder_schema.parent_folder_id is not None
            else folder.parent_folder_id
        )

        if next_parent_id is not None:
            parent = session.get(Folder, next_parent_id)
            if not parent:
                raise ValueError("Parent folder not found.")
            if parent.user_id != user_id:
                raise PermissionError("You do not have permission to use this folder.")

        FolderService._assert_parent_valid(folder_id, next_parent_id, session)
        FolderService._assert_folder_unique(user_id, next_parent_id, next_name, session, folder_id)

        folder.name = next_name
        folder.parent_folder_id = next_parent_id
        session.add(folder)
        session.commit()
        session.refresh(folder)
        return folder

    @staticmethod
    def delete_folder(folder_id: int, user_id: int, session: SessionDep) -> Folder:
        folder = FolderService._assert_folder_owner(folder_id, user_id, session)

        child = session.exec(
            select(Folder).where(Folder.parent_folder_id == folder_id)
        ).first()
        if child:
            raise ValueError("Folder has subfolders. Move or delete them first.")

        palette = session.exec(
            select(Palette).where(Palette.folder_id == folder_id)
        ).first()
        if palette:
            raise ValueError("Folder contains palettes. Move or delete them first.")

        session.delete(folder)
        session.commit()
        return folder
