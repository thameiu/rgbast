from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound
import jwt
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

    def check_auth_control(token: str, session: SessionDep):
        try:
            user = AuthService.check_auth(token, session)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )
            return user
        except jwt.exceptions.InvalidSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed",
            )
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
            )
