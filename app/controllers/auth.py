from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound
from app.schemas.auth import Login, LoginResponse
from app.core.database import SessionDep

from app.services.auth import AuthService


class AuthController:
    def login_control(loginSchema: Login, session: SessionDep) -> LoginResponse:
        try:
            loginResponse = AuthService.login(loginSchema, session)
            if loginResponse is None:
                raise NoResultFound
            return loginResponse

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )

        except NoResultFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invalid credentials"
            )

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )
