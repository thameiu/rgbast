from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from app.schemas.user import (
    UserCreate,
    UserCreateResponse,
    UserDeleteMeResponse,
    UserUpdateMe,
    UserUpdateMeResponse,
)
from app.core.database import SessionDep
from app.services.auth import AuthService
from app.services.user import UserService


class UserController:
    def create_user_control(userSchema: UserCreate, session: SessionDep):
        try:
            created_user = UserService.create_user(userSchema, session)
            sent = AuthService.send_verification_email(
                created_user,
                session,
                userSchema.verify_type,
            )
            if not sent:
                raise RuntimeError("Could not send verification email. Check SMTP configuration.")
            return UserCreateResponse(
                **created_user.model_dump(),
                response="User created succesfully !",
            )

        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )

        except IntegrityError as e:
            session.rollback()
            errorMessage = str(e.orig).lower()

            if "username" in errorMessage:
                detail = "This username is already taken."
            elif "email" in errorMessage:
                detail = "This email is already taken."
            else:
                detail = "A duplicate record already exists."

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )

    def get_user_from_username_control(username: str, session: SessionDep):
        return UserController.get_user_or_404_control(username, session)

    def get_user_or_404_control(username: str, session: SessionDep):
        user = UserService.get_user_from_username(username, session)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    @staticmethod
    def update_me_control(
        user_id: int,
        update_schema: UserUpdateMe,
        session: SessionDep,
    ) -> UserUpdateMeResponse:
        try:
            user, username_changed = UserService.update_me(user_id, update_schema, session)
            access_token = None
            if username_changed:
                access_token = AuthService.create_access_token_for_user(user)
            return UserUpdateMeResponse(
                id=user.id,
                username=user.username,
                firstname=user.firstname,
                lastname=user.lastname,
                birthdate=user.birthdate,
                access_token=access_token,
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)
            )
        except ValueError as e:
            message = str(e)
            code = status.HTTP_409_CONFLICT if "already taken" in message.lower() else status.HTTP_400_BAD_REQUEST
            raise HTTPException(status_code=code, detail=message)
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )

    @staticmethod
    def delete_me_control(user_id: int, session: SessionDep) -> UserDeleteMeResponse:
        try:
            UserService.delete_me(user_id, session)
            return UserDeleteMeResponse(response="Account deleted successfully.")
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )
