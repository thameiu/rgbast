import re
from datetime import datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class FolderCreate(SQLModel):
    name: str = Field(max_length=50)
    parent_folder_id: int | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def validate_name_folder_create(cls, name: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, name):
            raise ValueError("Folder name is invalid.")
        return name


class FolderCreateResponse(SQLModel):
    id: int
    user_id: int
    parent_folder_id: int | None
    name: str
    created_at: datetime


class FolderUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=50)
    parent_folder_id: int | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def validate_name_folder_update(cls, name: str | None) -> str | None:
        if name is None:
            return None
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, name):
            raise ValueError("Folder name is invalid.")
        return name


class FolderResponse(SQLModel):
    id: int
    user_id: int
    parent_folder_id: int | None
    name: str
    created_at: datetime


class FolderDeleteResponse(SQLModel):
    folder_id: int
    palette_strategy: str
    deleted_folder_ids: list[int] = Field(default=[])
    deleted_palette_ids: list[int] = Field(default=[])
    moved_palette_ids: list[int] = Field(default=[])
