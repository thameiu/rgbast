import os
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import RedirectResponse
from app.controllers.auth import AuthController
from app.core.database import SessionDep
from app.schemas.auth import (
    Login,
    LoginResponse,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    VerifyEmailCodeRequest,
    VerifyEmailResendRequest,
)
from app.schemas.user import UserMeResponse

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse, status_code=200)
def login_handler(login: Login, session: SessionDep):
    return AuthController.login_control(login, session)


@router.post("/check-auth", response_model=UserMeResponse, status_code=200)
def check_auth_handler(
    session: SessionDep,
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Inject it here
):
    # credentials.credentials contains just the raw JWT string (without "Bearer ")
    token = credentials.credentials
    return AuthController.check_auth_control(token, session)


@router.get("/verify-email", status_code=302)
def verify_email_handler(session: SessionDep, token: str = Query(...)):
    load_dotenv()
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    try:
        login_response = AuthController.verify_email_control(token, session)
        redirect_to = (
            f"{frontend_url}/auth/complete"
            f"?token={quote_plus(login_response.access_token)}&verified=1"
        )
    except Exception as e:
        reason = "invalid"
        detail = getattr(e, "detail", "")
        if isinstance(detail, str) and "expired" in detail.lower():
            reason = "expired"
        redirect_to = f"{frontend_url}/login?verified={reason}"
    return RedirectResponse(url=redirect_to, status_code=302)


@router.post("/verify-email/code", response_model=LoginResponse, status_code=200)
def verify_email_code_handler(payload: VerifyEmailCodeRequest, session: SessionDep):
    return AuthController.verify_email_code_control(payload, session)


@router.post("/verify-email/resend", response_model=MessageResponse, status_code=200)
def resend_verify_email_handler(payload: VerifyEmailResendRequest, session: SessionDep):
    return AuthController.resend_verification_email_control(payload, session)


@router.post(
    "/password-reset/request",
    response_model=MessageResponse,
    status_code=200,
)
def password_reset_request_handler(payload: PasswordResetRequest, session: SessionDep):
    return AuthController.request_password_reset_control(payload, session)


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=200,
)
def password_reset_confirm_handler(payload: PasswordResetConfirm, session: SessionDep):
    return AuthController.confirm_password_reset_control(payload, session)
