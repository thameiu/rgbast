from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound
import jwt
from app.schemas.auth import (
    Login,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    VerifyEmailCodeRequest,
    VerifyEmailResendRequest,
)
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

        except PermissionError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
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

    @staticmethod
    def verify_email_control(token: str, session: SessionDep) -> LoginResponse:
        try:
            user = AuthService.verify_email(token, session)
            access_token = AuthService.create_access_token_for_user(user)
            return LoginResponse(
                access_token=access_token,
                username=user.username,
                firstname=user.firstname,
                lastname=user.lastname,
                email=user.email,
            )
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Verification token has expired",
            )
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid verification token",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

    @staticmethod
    def verify_email_code_control(payload: VerifyEmailCodeRequest, session: SessionDep) -> LoginResponse:
        try:
            user = AuthService.verify_email_with_code(payload.email, payload.code, session)
            access_token = AuthService.create_access_token_for_user(user)
            return LoginResponse(
                access_token=access_token,
                username=user.username,
                firstname=user.firstname,
                lastname=user.lastname,
                email=user.email,
            )
        except ValueError as e:
            message = str(e)
            code = status.HTTP_400_BAD_REQUEST
            if "not found" in message.lower():
                code = status.HTTP_404_NOT_FOUND
            raise HTTPException(
                status_code=code,
                detail=message,
            )

    @staticmethod
    def resend_verification_email_control(
        payload: VerifyEmailResendRequest,
        session: SessionDep,
    ) -> MessageResponse:
        try:
            AuthService.resend_verification_email(payload.identifier, session)
            return MessageResponse(
                response=(
                    "If this account exists and is not yet verified, a new verification email has been sent."
                )
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )

    @staticmethod
    def request_password_reset_control(
        payload: PasswordResetRequest,
        session: SessionDep,
    ) -> MessageResponse:
        try:
            AuthService.request_password_reset(payload.email, session)
            return MessageResponse(
                response=(
                    "If this email exists, a password reset link has been sent."
                )
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )

    @staticmethod
    def confirm_password_reset_control(
        payload: PasswordResetConfirm,
        session: SessionDep,
    ) -> MessageResponse:
        try:
            AuthService.reset_password(payload.token, payload.password, session)
            return MessageResponse(response="Password reset successful.")
        except jwt.exceptions.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Reset token has expired",
            )
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid reset token",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. " + str(e),
            )
