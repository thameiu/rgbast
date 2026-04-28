from datetime import datetime

from sqlmodel import Field, SQLModel
from pydantic import field_validator
import re


class PaletteCreate(SQLModel):
    title: str = Field(max_length=50)
    description: str = Field(max_length=500)
    folder_id: int | None = Field(default=None)
    folder_path: list[str] | None = Field(default=None)
    palette_colors: list[PaletteColorSave] = Field(default=[])

    @field_validator("title")
    @classmethod
    def validate_title_palette_create(cls, title: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")
        return title

    @field_validator("folder_path")
    @classmethod
    def validate_folder_path_palette_create(cls, folder_path: list[str] | None) -> list[str] | None:
        if folder_path is None:
            return None
        pattern = r"^[a-zA-Z0-9._-]+$"
        for name in folder_path:
            if not re.match(pattern, name):
                raise ValueError("Folder path is invalid.")
        return folder_path


class PaletteCreateResponse(SQLModel):
    id: int
    title: str
    description: str
    folder_id: int | None
    folder_path: list[str] = Field(default=[])
    created_at: datetime


class PaletteSave(SQLModel):
    title: str
    description: str


class PaletteUpdate(SQLModel):
    title: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    folder_id: int | None = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title_palette_update(cls, title: str | None) -> str | None:
        if title is None:
            return None
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")
        return title


class PaletteColorSave(SQLModel):
    hex: str = Field(max_length=6)
    label: str | None = Field(max_length=50)


class PaletteSnapshotSave(SQLModel):
    parent_snapshot_id: int | None = Field(default=None)  # branch point
    branch_id: int | None = Field(default=None)
    create_branch: bool = Field(default=False)
    branch_title: str | None = Field(default=None, max_length=100)
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)


class PaletteSnapshotSaveResponse(SQLModel):
    palette_id: int
    palette_snapshot_id: int
    parent_snapshot_id: int | None
    branch_id: int | None = Field(default=None)
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)
    created_at: datetime
    colors_added: int = Field(default=0)
    colors_deleted: int = Field(default=0)
    colors_modified: int = Field(default=0)


# A single commit in the tree
class PaletteCommitResponse(SQLModel):
    id: int
    palette_id: int
    parent_snapshot_id: int | None
    branch_id: int | None = Field(default=None)
    comment: str | None
    created_at: datetime
    palette_colors: list[PaletteColorSave] = Field(default=[])
    colors_added: int = Field(default=0)
    colors_deleted: int = Field(default=0)
    colors_modified: int = Field(default=0)


class PaletteBranchHistoryResponse(SQLModel):
    id: int
    title: str
    merged_at: datetime | None = Field(default=None)
    is_merged: bool = Field(default=False)
    snapshots: list[PaletteCommitResponse] = Field(default=[])


# The overall repository history
class PaletteHistoryGraphResponse(SQLModel):
    palette_id: int
    owner_username: str
    title: str
    description: str | None = Field(default=None)
    folder_path: list[str] = Field(default=[])
    main: list[PaletteCommitResponse] = Field(default=[])
    branches: list[PaletteBranchHistoryResponse] = Field(default=[])


class PaletteBranchMergeResponse(SQLModel):
    palette_id: int
    branch_id: int
    merged_at: datetime
    palette_snapshot_id: int
    parent_snapshot_id: int | None
    comment: str | None
    created_at: datetime
    palette_colors: list[PaletteColorSave] = Field(default=[])
    colors_added: int = Field(default=0)
    colors_deleted: int = Field(default=0)
    colors_modified: int = Field(default=0)


class PaletteDeleteResponse(SQLModel):
    palette_id: int
    deleted_branches: int = Field(default=0)
    deleted_snapshots: int = Field(default=0)
    deleted_colors: int = Field(default=0)
    deleted_changes: int = Field(default=0)


class PaletteBranchDeleteResponse(SQLModel):
    palette_id: int
    branch_id: int
    deleted_snapshots: int = Field(default=0)
    deleted_colors: int = Field(default=0)
    deleted_changes: int = Field(default=0)


class PaletteBranchRevertResponse(SQLModel):
    palette_id: int
    branch_id: int
    target_snapshot_id: int
    latest_snapshot_id: int
    deleted_snapshots: int = Field(default=0)
    deleted_colors: int = Field(default=0)
    deleted_changes: int = Field(default=0)


class PaletteMainRevertResponse(SQLModel):
    palette_id: int
    target_snapshot_id: int
    latest_snapshot_id: int
    deleted_snapshots: int = Field(default=0)
    deleted_branches: int = Field(default=0)
    deleted_colors: int = Field(default=0)
    deleted_changes: int = Field(default=0)


class PaletteByUsernameItemResponse(SQLModel):
    id: int
    title: str
    description: str | None = Field(default=None)
    folder_id: int | None = Field(default=None)
    folder_path: list[str] = Field(default=[])
    created_at: datetime
    latest_main_snapshot: PaletteCommitResponse | None = Field(default=None)


class PaletteByUsernameResponse(SQLModel):
    username: str
    palettes: list[PaletteByUsernameItemResponse] = Field(default=[])
