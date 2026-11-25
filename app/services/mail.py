import os
import smtplib
import ssl
import logging
from urllib.parse import quote
from email.message import EmailMessage

from dotenv import load_dotenv


class MailService:
    @staticmethod
    def _is_enabled() -> bool:
        load_dotenv()
        return os.getenv("SMTP_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def send_email(to_email: str, subject: str, text_body: str, html_body: str | None = None) -> bool:
        load_dotenv()
        if not MailService._is_enabled():
            return False

        smtp_host = os.getenv("SMTP_HOST", "smtp.ionos.fr")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        smtp_username = os.getenv("SMTP_USERNAME", "support@rgbast.com")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_from = os.getenv("SMTP_FROM", smtp_username)
        use_ssl = os.getenv("SMTP_USE_SSL", "true").lower() in {"1", "true", "yes", "on"}

        if not smtp_password:
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = smtp_from
        message["To"] = to_email
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=15) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        return True

    @staticmethod
    def notify(to_email: str, subject: str, body: str, path: str) -> bool:
        """Best-effort notifications, called only after the action commits."""
        url = os.getenv("FRONTEND_URL", "https://rgbast.com").rstrip("/") + path
        try:
            return MailService.send_email(to_email, subject, f"{body}\n\n{url}")
        except (OSError, smtplib.SMTPException, ValueError):
            logging.getLogger("rgbast.mail").exception("Notification email failed")
            return False

    @staticmethod
    def colleague_request(to_email: str, username: str) -> bool:
        return MailService.notify(
            to_email,
            "RGBAST - New colleague request",
            f"{username} has sent you a colleague request on RGBAST.\n"
            "Sign in to view their profile and accept or decline the request.",
            f"/users/{quote(username, safe='')}",
        )

    @staticmethod
    def project_invitation(to_email: str, username: str, project_title: str) -> bool:
        return MailService.notify(
            to_email,
            "RGBAST - Project invitation",
            f'{username} has invited you to join the project "{project_title}" on RGBAST.\n'
            "Sign in and open Projects in your Atelier to accept or decline the invitation.\n"
            "You will receive access only after accepting the invitation.",
            "/atelier/projects",
        )
