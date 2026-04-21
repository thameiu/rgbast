from datetime import datetime

from sqlmodel import Field, SQLModel
from pydantic import field_validator
import re


class PaletteCreate(SQLModel):
    title: str = Field(max_length=50)
    description: str = Field(max_length=500)
    palette_colors: list[PaletteColorSave] = Field(default=[])

    @field_validator("title")
    @classmethod
    def validate_title_palette_create(cls, title: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")
        return title


class PaletteCreateResponse(SQLModel):
    id: int
    title: str
    description: str
    created_at: datetime


class PaletteSave(SQLModel):
    title: str
    description: str


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
