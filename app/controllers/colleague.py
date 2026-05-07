from fastapi import HTTPException, status

from app.core.database import SessionDep
from app.schemas.colleague import (
    ColleagueActionResponse,
    ColleagueCountResponse,
    ColleagueDeleteResponse,
    ColleagueListResponse,
    ColleaguePublicListResponse,
    ColleagueStatusResponse,
)
from app.services.colleague import ColleagueService


class ColleagueController:
    @staticmethod
    def list_me_control(current_user_id: int, session: SessionDep) -> ColleagueListResponse:
        try:
            return ColleagueListResponse(**ColleagueService.list_for_user(current_user_id, session))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def add_or_accept_control(
        current_user_id: int,
        target_username: str,
        session: SessionDep,
    ) -> ColleagueActionResponse:
        try:
            state, user, message = ColleagueService.send_or_accept(current_user_id, target_username, session)
            return ColleagueActionResponse(status=state, user=user, response=message)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def accept_control(
        current_user_id: int,
        from_username: str,
        session: SessionDep,
    ) -> ColleagueActionResponse:
        try:
            state, user, message = ColleagueService.accept_request(current_user_id, from_username, session)
            return ColleagueActionResponse(status=state, user=user, response=message)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def delete_control(
        current_user_id: int,
        target_username: str,
        session: SessionDep,
    ) -> ColleagueDeleteResponse:
        try:
            state, user, message = ColleagueService.remove_relation(current_user_id, target_username, session)
            return ColleagueDeleteResponse(status=state, user=user, response=message)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def get_status_control(
        current_user_id: int,
        target_username: str,
        session: SessionDep,
    ) -> ColleagueStatusResponse:
        try:
            relation = ColleagueService.get_relation_status(current_user_id, target_username, session)
            return ColleagueStatusResponse(status=relation)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def get_count_by_username_control(username: str, session: SessionDep) -> ColleagueCountResponse:
        try:
            user = ColleagueService._get_user_by_username_or_404(username, session)
            count = ColleagueService.count_colleagues(user.id, session)
            return ColleagueCountResponse(username=user.username, colleagues_count=count)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @staticmethod
    def list_public_by_username_control(username: str, session: SessionDep) -> ColleaguePublicListResponse:
        try:
            return ColleaguePublicListResponse(**ColleagueService.list_public_by_username(username, session))
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
