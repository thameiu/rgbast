from pydantic import BaseModel, Field, field_validator

from app.models.project import PERMISSIONS
from typing import Literal
from app.schemas.palette import PaletteCreate


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    slug: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=5000)
    private: bool = False

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Title cannot be empty.")
        return value.strip()


class ProjectUpdate(ProjectCreate):
    pass


class ProjectMemberInput(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    permissions: list[str]

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, value):
        if not value or set(value) - set(PERMISSIONS):
            raise ValueError("Invalid project permissions.")
        return sorted(set(value) | {"read"})


class ProjectDelete(BaseModel):
    confirm_title: str


class ProjectPaletteAdd(PaletteCreate):
    source_palette_id: int | None = None
    mode: Literal['copy', 'move'] = 'copy'
