from datetime import datetime

from pydantic import field_validator
from sqlmodel import Field, SQLModel
from app.services.color import ColorService


class ColorBookmarkUpsert(SQLModel):
    label: str = Field(max_length=100)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        label = value.strip()
        if not label:
            raise ValueError("Label cannot be empty.")
        return label


class ColorBookmarkResponse(SQLModel):
    project_id: int | None = None
    id: int
    user_id: int
    hex: str
    label: str
    created_at: datetime
    updated_at: datetime


class ColorBookmarkListResponse(SQLModel):
    bookmarks: list[ColorBookmarkResponse] = Field(default_factory=list)


class ColorBookmarkByUsernameResponse(SQLModel):
    username: str
    bookmarks: list[ColorBookmarkResponse] = Field(default_factory=list)


class ColorBookmarkDeleteResponse(SQLModel):
    id: int
    hex: str
    deleted: bool


class ColorBookmarkCreate(ColorBookmarkUpsert):
    hex: str
    project_id: int | None = None

    @field_validator("hex")
    @classmethod
    def validate_hex(cls, value: str) -> str:
        return ColorService._normalize_hex(value)
