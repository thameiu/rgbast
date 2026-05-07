from fastapi import APIRouter, Query

from app.controllers.search import SearchController
from app.core.database import SessionDep
from app.schemas.search import PaletteSearchResponse, UserSearchResponse

router = APIRouter()


@router.get("/search/users", response_model=UserSearchResponse, status_code=200)
def search_users_handler(
    session: SessionDep,
    q: str = Query(..., min_length=1, max_length=100),
):
    return SearchController.search_users_control(q, session)


@router.get("/search/palettes", response_model=PaletteSearchResponse, status_code=200)
def search_palettes_handler(
    session: SessionDep,
    query: str | None = Query(default=None, min_length=1, max_length=120),
    colors: str | None = Query(default=None, description="Comma-separated HEX values"),
    color_mode: str = Query(default="exact"),
):
    return SearchController.search_palettes_control(session, query, colors, color_mode)
