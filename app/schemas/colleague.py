from typing import Literal

from sqlmodel import SQLModel


ColleagueRelationStatus = Literal[
    "self",
    "none",
    "pending_outgoing",
    "pending_incoming",
    "accepted",
]


class ColleagueUserResponse(SQLModel):
    id: int
    username: str
    firstname: str | None
    lastname: str | None


class ColleagueListResponse(SQLModel):
    colleagues: list[ColleagueUserResponse]
    outgoing_pending: list[ColleagueUserResponse]
    incoming_pending: list[ColleagueUserResponse]
    incoming_count: int


class ColleagueActionResponse(SQLModel):
    status: Literal["pending", "accepted", "removed"]
    user: ColleagueUserResponse
    response: str


class ColleagueDeleteResponse(SQLModel):
    status: Literal["removed"]
    user: ColleagueUserResponse
    response: str


class ColleagueStatusResponse(SQLModel):
    status: ColleagueRelationStatus


class ColleagueCountResponse(SQLModel):
    username: str
    colleagues_count: int


class ColleaguePublicListResponse(SQLModel):
    username: str
    colleagues: list[ColleagueUserResponse]
    total: int
