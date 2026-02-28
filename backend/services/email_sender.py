"""
backend/services/email_sender.py

Thin wrapper around Resend for transactional emails.
Used for human-escalation briefings, notifications, etc.
"""

import resend

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def send_email(
    to: str,
    subject: str,
    body: str,
    contact_name: str | None = None,
) -> dict:
    """
    Send a plain-text email via Resend.
    Returns the Resend API response dict.
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.error("RESEND_API_KEY not configured — cannot send email")
        raise RuntimeError("Resend API key not configured")

    resend.api_key = settings.resend_api_key

    params: resend.Emails.SendParams = {
        "from": "Miroir Collections <onboarding@resend.dev>",
        "to": [to],
        "subject": subject,
        "text": body,
    }

    response = resend.Emails.send(params)

    logger.info(
        "Email sent via Resend — to: %s subject: %s contact: %s",
        to,
        subject,
        contact_name or "N/A",
    )

    return response
