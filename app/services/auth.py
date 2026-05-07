from datetime import datetime, timedelta, timezone
import hashlib
import os
import re
import secrets
from urllib.parse import quote_plus

from dotenv import load_dotenv
import jwt
from sqlmodel import select

from app.models.user import User
from app.schemas.auth import Login, LoginResponse
from app.core.database import SessionDep
from pwdlib import PasswordHash

from app.schemas.user import UserMeResponse, UserUtils
from app.services.mail import MailService
from app.services.user import UserService

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 60
VERIFY_TOKEN_EXPIRE_HOURS = 48
VERIFY_CODE_EXPIRE_MINUTES = 20
RESET_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    @staticmethod
    def _get_secret_key() -> str:
        load_dotenv()
        return os.getenv("SECRET_KEY", "key_and_peele")

    @staticmethod
    def _get_frontend_url() -> str:
        load_dotenv()
        return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    @staticmethod
    def _get_backend_public_url() -> str:
        load_dotenv()
        return os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")

    @staticmethod
    def _create_scoped_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
        to_encode = {
            "sub": subject,
            "type": token_type,
            "exp": datetime.now(timezone.utc) + expires_delta,
        }
        return jwt.encode(to_encode, AuthService._get_secret_key(), algorithm=ALGORITHM)

    @staticmethod
    def _decode_scoped_token(token: str, expected_type: str) -> dict:
        decoded = jwt.decode(jwt=token, key=AuthService._get_secret_key(), algorithms=[ALGORITHM])
        token_type = decoded.get("type")
        if token_type != expected_type:
            raise jwt.exceptions.InvalidTokenError("Invalid token scope")
        return decoded

    @staticmethod
    def _build_verify_url(token: str) -> str:
        return f"{AuthService._get_backend_public_url()}/verify-email?token={quote_plus(token)}"

    @staticmethod
    def _build_reset_url(token: str) -> str:
        return f"{AuthService._get_frontend_url()}/reset-password?token={quote_plus(token)}"

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _create_email_verify_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _hash_email_verify_code(user: User, code: str) -> str:
        payload = f"{user.id}:{AuthService._normalize_email(user.email)}:{code}:{AuthService._get_secret_key()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def login(loginSchema: Login, session: SessionDep) -> LoginResponse:
        hasher = PasswordHash.recommended()
        if "@" in loginSchema.username:
            query = select(User).where(User.email == loginSchema.username)
        else:
            query = select(User).where(User.username == loginSchema.username)

        # Team tout à la fois ou vérifications séparées ? A vos claviers !
        result = session.exec(query).first()
        if result and hasher.verify(loginSchema.password, result.password):
            if not result.is_email_verified:
                raise PermissionError("Email not verified. Please verify your address from the email link.")
            access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
            token = AuthService.create_access_token(
                data={"sub": result.username},
                expires_delta=access_token_expires,
            )
            return LoginResponse(
                access_token=token,
                username=result.username,
                firstname=result.firstname,
                lastname=result.lastname,
                email=result.email,
            )
        return None

    @staticmethod
    def send_verification_link_email(user: User) -> bool:
        token = AuthService._create_scoped_token(
            subject=user.username,
            token_type="email_verify",
            expires_delta=timedelta(hours=VERIFY_TOKEN_EXPIRE_HOURS),
        )
        verify_url = AuthService._build_verify_url(token)
        subject = "Verify your RGBAST email"
        text_body = (
            f"Hi {user.username},\n\n"
            "Please verify your email to activate your RGBAST account.\n"
            f"{verify_url}\n\n"
            "If you did not create an account, you can ignore this email."
        )
        html_body = (
            f"<p>Hi {user.username},</p>"
            "<p>Please verify your email to activate your RGBAST account.</p>"
            f"<p><a href=\"{verify_url}\">Verify my email</a></p>"
            "<p>If you did not create an account, you can ignore this email.</p>"
        )
        return MailService.send_email(user.email, subject, text_body, html_body)

    @staticmethod
    def send_verification_code_email(user: User, session: SessionDep) -> bool:
        code = AuthService._create_email_verify_code()
        user.email_verify_code_hash = AuthService._hash_email_verify_code(user, code)
        user.email_verify_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=VERIFY_CODE_EXPIRE_MINUTES
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        subject = "Your RGBAST verification code"
        text_body = (
            f"Hi {user.username},\n\n"
            "Use this verification code to activate your RGBAST account:\n"
            f"{code}\n\n"
            f"The code expires in {VERIFY_CODE_EXPIRE_MINUTES} minutes.\n"
            "If you did not create an account, you can ignore this email."
        )
        html_body = (
            f"<p>Hi {user.username},</p>"
            "<p>Use this verification code to activate your RGBAST account:</p>"
            f"<p><strong style=\"font-size:20px;letter-spacing:0.15em;\">{code}</strong></p>"
            f"<p>The code expires in {VERIFY_CODE_EXPIRE_MINUTES} minutes.</p>"
            "<p>If you did not create an account, you can ignore this email.</p>"
        )
        return MailService.send_email(user.email, subject, text_body, html_body)

    @staticmethod
    def send_verification_email(user: User, session: SessionDep, verify_type: str = "link") -> bool:
        if verify_type == "code":
            return AuthService.send_verification_code_email(user, session)
        return AuthService.send_verification_link_email(user)

    @staticmethod
    def send_password_reset_email(user: User) -> bool:
        token = AuthService._create_scoped_token(
            subject=user.username,
            token_type="password_reset",
            expires_delta=timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
        )
        reset_url = AuthService._build_reset_url(token)
        subject = "Reset your RGBAST password"
        text_body = (
            f"Hi {user.username},\n\n"
            "Use this link to reset your password:\n"
            f"{reset_url}\n\n"
            "If you did not request this change, you can ignore this email."
        )
        html_body = (
            f"<p>Hi {user.username},</p>"
            "<p>Use this link to reset your password:</p>"
            f"<p><a href=\"{reset_url}\">Reset my password</a></p>"
            "<p>If you did not request this change, you can ignore this email.</p>"
        )
        return MailService.send_email(user.email, subject, text_body, html_body)

    @staticmethod
    def verify_email(token: str, session: SessionDep) -> User:
        decoded = AuthService._decode_scoped_token(token, "email_verify")
        username = str(decoded.get("sub") or "")
        user = UserService.get_user_model_by_username(username, session)
        if user is None:
            raise ValueError("User not found.")
        if not user.is_email_verified:
            user.is_email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            user.email_verify_code_hash = None
            user.email_verify_code_expires_at = None
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    @staticmethod
    def verify_email_with_code(email: str, code: str, session: SessionDep) -> User:
        normalized_email = AuthService._normalize_email(email)
        normalized_code = code.strip()
        if not re.fullmatch(r"\d{6}", normalized_code):
            raise ValueError("Invalid verification code.")

        user = UserService.get_user_model_by_email(normalized_email, session)
        if user is None:
            raise ValueError("User not found.")
        if user.is_email_verified:
            return user
        if not user.email_verify_code_hash or not user.email_verify_code_expires_at:
            raise ValueError("No active verification code.")

        now = datetime.now(timezone.utc)
        expires_at = user.email_verify_code_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise ValueError("Verification code has expired.")

        incoming_hash = AuthService._hash_email_verify_code(user, normalized_code)
        if incoming_hash != user.email_verify_code_hash:
            raise ValueError("Invalid verification code.")

        user.is_email_verified = True
        user.email_verified_at = now
        user.email_verify_code_hash = None
        user.email_verify_code_expires_at = None
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @staticmethod
    def resend_verification_email(identifier: str, session: SessionDep) -> bool:
        raw = identifier.strip()
        if not raw:
            return False

        user: User | None
        if "@" in raw:
            user = UserService.get_user_model_by_email(raw, session)
        else:
            user = UserService.get_user_model_by_username(raw, session)

        if user is None or user.is_email_verified:
            return False

        return AuthService.send_verification_link_email(user)

    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        return AuthService.create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires,
        )

    @staticmethod
    def request_password_reset(email: str, session: SessionDep) -> None:
        user = UserService.get_user_model_by_email(email.strip().lower(), session)
        if not user:
            return
        AuthService.send_password_reset_email(user)

    @staticmethod
    def reset_password(token: str, new_password: str, session: SessionDep) -> None:
        if not UserUtils.validate_password(new_password):
            raise ValueError("Password is too weak.")
        decoded = AuthService._decode_scoped_token(token, "password_reset")
        username = str(decoded.get("sub") or "")
        user = UserService.get_user_model_by_username(username, session)
        if user is None:
            raise ValueError("User not found.")
        hasher = PasswordHash.recommended()
        user.password = hasher.hash(new_password)
        session.add(user)
        session.commit()

    def check_auth(token: str, session: SessionDep):
        secret_key = AuthService._get_secret_key()
        decoded_token = jwt.decode(jwt=token, key=secret_key, algorithms=[ALGORITHM])
        username = decoded_token.get("sub")
        user = UserService.get_user_model_by_username(username, session)
        if user is None:
            return None
        public_user = UserService.get_user_from_username(user.username, session)
        if public_user is None:
            return None
        return UserMeResponse(
            **public_user.model_dump(),
            email=user.email,
        )

    def create_access_token(data: dict, expires_delta: timedelta | None = None):
        to_encode = data.copy()
        expire = (
            datetime.now(timezone.utc) + expires_delta
            if expires_delta
            else datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        )
        to_encode.update({"exp": expire})
        secret_key = AuthService._get_secret_key()
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
        return encoded_jwt
