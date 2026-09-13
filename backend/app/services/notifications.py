import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    """通知メールの送信に失敗した場合に送出する。"""


async def send_alert_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise NotificationError("SMTP_HOST / SMTP_FROM_EMAIL が設定されていません")

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
    except aiosmtplib.SMTPException as exc:
        raise NotificationError(f"通知メールの送信に失敗しました ({type(exc).__name__})") from None
