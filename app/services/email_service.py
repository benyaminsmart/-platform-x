"""Email service — sends emails via Resend.

Disabled by default. Enable via EMAIL_ENABLED=true and RESEND_API_KEY.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """Return True if email sending is properly configured."""
    return bool(settings.EMAIL_ENABLED and settings.RESEND_API_KEY)


def send_email(
    to: str,
    subject: str,
    html: str,
    text: str | None = None,
) -> bool:
    """Send an email via Resend. Returns True on success.

    If email is disabled or misconfigured, logs and returns False
    without raising — so callers don't break when email is off.
    """
    if not is_enabled():
        logger.info("Email disabled; would send to=%s subject=%s", to, subject)
        return False

    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY

        params = {
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            params["text"] = text

        resend.Emails.send(params)
        logger.info("Email sent to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        logger.error("Email send failed to=%s subject=%s error=%s", to, subject, exc)
        return False
