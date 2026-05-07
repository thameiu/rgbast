from fastapi import HTTPException, status

from app.core.database import SessionDep
from app.schemas.search import PaletteSearchResponse, UserSearchResponse
from app.services.palette import PaletteService
from app.services.user import UserService


class SearchController:
    @staticmethod
    def search_users_control(query: str, session: SessionDep) -> UserSearchResponse:
        try:
            results = UserService.search_users(query, session, limit=100)
            return UserSearchResponse(query=query, total=len(results), results=results)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

    @staticmethod
    def search_palettes_control(
        session: SessionDep,
        query: str | None,
        colors: str | None,
        color_mode: str,
    ) -> PaletteSearchResponse:
        try:
            color_list = []
            if colors:
                color_list = [c.strip() for c in colors.split(",") if c.strip()]
            results = PaletteService.search_palettes(
                session=session,
                title_query=query,
                colors=color_list,
                color_mode=color_mode,
                limit=100,
            )
            return PaletteSearchResponse(
                query=query,
                colors=color_list,
                color_mode=color_mode,
                total=len(results),
                results=results,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
