from typing import Literal

from sqlmodel import select

from app.core.database import SessionDep
from app.models.folder import Folder
from app.models.palette import Palette
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate
from app.services.palette import PaletteService


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
    def _collect_descendant_folder_ids(
        root_folder_id: int,
        user_id: int,
        session: SessionDep,
    ) -> tuple[list[int], dict[int, int]]:
        folders = session.exec(select(Folder).where(Folder.user_id == user_id)).all()
        children_by_parent: dict[int, list[int]] = {}
        for folder in folders:
            parent_id = folder.parent_folder_id
            if parent_id is None:
                continue
            children_by_parent.setdefault(parent_id, []).append(folder.id)

        ordered_ids: list[int] = []
        depth_by_id: dict[int, int] = {}
        stack: list[tuple[int, int]] = [(root_folder_id, 0)]

        while stack:
            folder_id, depth = stack.pop()
            ordered_ids.append(folder_id)
            depth_by_id[folder_id] = depth
            for child_id in children_by_parent.get(folder_id, []):
                stack.append((child_id, depth + 1))

        return ordered_ids, depth_by_id

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
        folder_schema: FolderCreate,
        user_id: int,
        session: SessionDep,
    ) -> Folder:
        FolderService._assert_unique_name(
            user_id, folder_schema.parent_folder_id, folder_schema.name, session
        )

        if folder_schema.parent_folder_id is not None:
            parent = session.get(Folder, folder_schema.parent_folder_id)
            if not parent:
                raise ValueError("Parent folder not found.")
            if parent.user_id != user_id:
                raise PermissionError("You do not have permission to use this parent folder.")

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
        next_parent = (
            folder_schema.parent_folder_id
            if folder_schema.parent_folder_id is not None
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
    def delete_folder(
        folder_id: int,
        user_id: int,
        palette_strategy: Literal["move_root", "delete"],
        session: SessionDep,
    ) -> dict:
        folder = FolderService._assert_folder_owner(folder_id, user_id, session)
        descendant_ids, depth_by_id = FolderService._collect_descendant_folder_ids(folder.id, user_id, session)

        palettes_in_tree = session.exec(
            select(Palette).where(
                Palette.user_id == user_id,
                Palette.folder_id.in_(descendant_ids),
            )
        ).all()
        palette_ids = [palette.id for palette in palettes_in_tree]

        deleted_palette_ids: list[int] = []
        moved_palette_ids: list[int] = []

        if palette_strategy == "delete":
            for palette_id in palette_ids:
                PaletteService.delete_palette(palette_id, user_id, session)
                deleted_palette_ids.append(palette_id)
        else:
            for palette in palettes_in_tree:
                palette.folder_id = None
                session.add(palette)
                moved_palette_ids.append(palette.id)
            session.commit()

        # Delete children first, then the requested folder.
        deletion_order = sorted(descendant_ids, key=lambda value: depth_by_id.get(value, 0), reverse=True)
        for current_id in deletion_order:
            current_folder = session.get(Folder, current_id)
            if current_folder is not None:
                session.delete(current_folder)

        session.commit()

        return {
            "folder_id": folder_id,
            "palette_strategy": palette_strategy,
            "deleted_folder_ids": deletion_order,
            "deleted_palette_ids": deleted_palette_ids,
            "moved_palette_ids": moved_palette_ids,
        }
