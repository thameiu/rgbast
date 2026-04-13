from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from app.schemas.user import UserCreate, UserCreateResponse
from app.core.database import SessionDep
from app.services.user import UserService


class UserController:
    def create_user_control(userSchema: UserCreate, session: SessionDep):
        try:
            return UserCreateResponse(
                **(UserService.create_user(userSchema, session)).model_dump(),
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
