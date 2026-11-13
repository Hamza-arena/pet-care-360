import logging
import smtplib
from abc import ABC, abstractmethod
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import ClassVar

from flask import current_app

logger = logging.getLogger('petcare360.notifications')


class BaseNotificationService(ABC):
    """Abstract base class for all notification providers."""

    @abstractmethod
    def send_email(self, to: str, subject: str, body: str, html: str | None = None) -> bool:
        """Send an email notification."""

    @abstractmethod
    def send_sms(self, to: str, message: str) -> bool:
        """Send an SMS notification."""


class ConsoleNotificationService(BaseNotificationService):
    """Development and testing notification service that records dispatched messages

    in an in-memory outbox list for test inspection.
    """

    outbox: ClassVar[list[dict]] = []

    def send_email(self, to: str, subject: str, body: str, html: str | None = None) -> bool:
        record = {
            'type': 'email',
            'to': to,
            'subject': subject,
            'body': body,
            'html': html,
            'sent_at': datetime.now(UTC),
        }
        self.outbox.append(record)
        logger.info(f"[CONSOLE EMAIL] To: {to} | Subject: {subject} | Body: {body[:80]}...")
        return True

    def send_sms(self, to: str, message: str) -> bool:
        record = {
            'type': 'sms',
            'to': to,
            'message': message,
            'sent_at': datetime.now(UTC),
        }
        self.outbox.append(record)
        logger.info(f"[CONSOLE SMS] To: {to} | Message: {message}")
        return True

    @classmethod
    def clear_outbox(cls):
        cls.outbox.clear()

    @classmethod
    def clear(cls):
        cls.outbox.clear()

    @property
    def email_outbox(self):
        return [m for m in self.outbox if m['type'] == 'email']

    @property
    def sms_outbox(self):
        return [m for m in self.outbox if m['type'] == 'sms']


class SmtpNotificationService(BaseNotificationService):
    """Production SMTP email notification service."""

    def __init__(self, server=None, port=None, username=None, password=None, use_tls=True, default_sender=None):
        self.server = server
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.default_sender = default_sender

    def send_email(self, to: str, subject: str, body: str, html: str | None = None) -> bool:
        sender = self.default_sender or 'notifications@petcare360.com'
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to

        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        if html:
            part2 = MIMEText(html, 'html')
            msg.attach(part2)

        try:
            with smtplib.SMTP(self.server, self.port, timeout=10) as s:
                if self.use_tls:
                    s.starttls()
                if self.username and self.password:
                    s.login(self.username, self.password)
                s.sendmail(sender, [to], msg.as_string())
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {to}: {e}")
            raise

    def send_sms(self, to: str, message: str) -> bool:
        # Fallback to logger when SMS gateway not plugged
        logger.info(f"[SMTP BACKEND SMS FALLBACK] To: {to} | Message: {message}")
        return True


def get_notification_service() -> BaseNotificationService:
    """Factory returning the configured notification service based on app config."""
    try:
        backend = current_app.config.get('MAIL_BACKEND', 'console')
    except RuntimeError:
        backend = 'console'

    if backend == 'smtp':
        return SmtpNotificationService(
            server=current_app.config.get('MAIL_SERVER'),
            port=current_app.config.get('MAIL_PORT', 587),
            username=current_app.config.get('MAIL_USERNAME'),
            password=current_app.config.get('MAIL_PASSWORD'),
            use_tls=current_app.config.get('MAIL_USE_TLS', True),
            default_sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
        )

    return ConsoleNotificationService()

