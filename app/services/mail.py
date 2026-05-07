import os
import smtplib
import ssl
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
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(smtp_username, smtp_password)
                server.send_message(message)
        return True
