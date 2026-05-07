from datetime import datetime
from sqlmodel import SQLModel


class UserSearchItem(SQLModel):
    id: int
    username: str
    firstname: str | None
    lastname: str | None


class UserSearchResponse(SQLModel):
    query: str
    total: int
    results: list[UserSearchItem]


class PaletteSearchColor(SQLModel):
    hex: str
    label: str | None


class PaletteSearchItem(SQLModel):
    id: int
    owner_username: str
    title: str
    description: str | None
    folder_path: list[str]
    created_at: datetime
    latest_main_snapshot_created_at: datetime | None
    palette_colors: list[PaletteSearchColor]


class PaletteSearchResponse(SQLModel):
    query: str | None
    colors: list[str]
    color_mode: str
    total: int
    results: list[PaletteSearchItem]
