from fastapi import APIRouter, Depends, Query

from app.controllers.search import SearchController
from app.core.database import SessionDep
from app.middlewares.auth import verify_token
from app.schemas.search import DiscoverPalettesResponse, PaletteSearchResponse, UserSearchResponse

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


@router.get("/discover/palettes/recent", response_model=DiscoverPalettesResponse, status_code=200)
def discover_recent_palettes_handler(
    session: SessionDep,
    limit: int = Query(default=24, ge=1, le=60),
):
    return SearchController.discover_recent_palettes_control(session, limit)


@router.get("/discover/palettes/colleagues", response_model=DiscoverPalettesResponse, status_code=200)
def discover_colleague_palettes_handler(
    session: SessionDep,
    limit: int = Query(default=12, ge=1, le=60),
    current_user=Depends(verify_token),
):
    return SearchController.discover_colleague_palettes_control(current_user.id, session, limit)
