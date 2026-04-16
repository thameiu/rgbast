from datetime import datetime

from sqlmodel import Field, SQLModel
from pydantic import field_validator
import re


class PaletteCreate(SQLModel):
    user_id: int
    title: str = Field(max_length=50)
    description: str = Field(max_length=500)

    @field_validator("title")
    @classmethod
    def validate_title_palette_create(cls, title: str) -> str:
        pattern = r"^[a-zA-Z0-9._-]+$"
        if not re.match(pattern, title):
            raise ValueError("Title is invalid.")
        return title


class PaletteCreateResponse(SQLModel):
    title: str
    description: str
    created_at: datetime


class PaletteSave(SQLModel):
    title: str
    description: str


class PaletteColorSave(SQLModel):
    hex: str = Field(max_length=6)
    label: str = Field(max_length=50)


class PaletteSnapshotSave(SQLModel):
    palette_id: int
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)


class PaletteSnapshotSaveResponse(SQLModel):
    palette_id: int
    palette_snapshot_id: int
    palette_colors: list[PaletteColorSave] = Field(default=[])
    comment: str = Field(max_length=500)
    created_at: datetime
