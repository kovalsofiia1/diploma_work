import logging
import resend
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(
    *,
    to_email: str,
    subject: str,
    html: str,
    plain_text: str | None = None,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> None:
    """Send mail via Resend if configured, otherwise fall back to SMTP.

    Resend works over HTTPS, which is required on hosts that block outbound
    SMTP ports (e.g. Render's free tier). Locally we usually have SMTP
    configured, so the fallback keeps dev unchanged.
    """
    settings = get_settings()
    if settings.resend_api_key and settings.resend_from_email:
        try:
            send_email_via_resend(
                to_email=to_email,
                subject=subject,
                html=html,
                attachments=attachments,
            )
            return
        except Exception:
            logger.exception(
                "Resend send failed; falling back to SMTP if configured"
            )
    send_email_via_smtp(
        to_email=to_email,
        subject=subject,
        html=html,
        plain_text=plain_text,
        attachments=attachments,
    )


def _send_email_preferring_resend(
    *,
    to_email: str,
    subject: str,
    html: str,
    plain_text: str | None = None,
) -> None:
    send_email(
        to_email=to_email, subject=subject, html=html, plain_text=plain_text
    )


def send_registration_code_email(email: str, code: str) -> None:
    settings = get_settings()
    subject = "Your verification code"
    plain_text = (
        f"Your verification code is: {code}\n"
        f"This code expires in {settings.email_verification_code_ttl_minutes} minutes."
    )
    html_text = (
        "<p>Your verification code is:</p>"
        f"<h2>{code}</h2>"
        f"<p>This code expires in {settings.email_verification_code_ttl_minutes} minutes.</p>"
    )
    _send_email_preferring_resend(
        to_email=email,
        subject=subject,
        html=html_text,
        plain_text=plain_text,
    )

def send_password_reset_code_email(email: str, code: str) -> None:
    settings = get_settings()

    subject = "Your password reset code"
    plain_text = (
        f"Your password reset code is: {code}\n"
        f"This code expires in {settings.email_verification_code_ttl_minutes} minutes."
    )
    html_text = (
        "<p>Your password reset code is:</p>"
        f"<h2>{code}</h2>"
        f"<p>This code expires in {settings.email_verification_code_ttl_minutes} minutes.</p>"
    )
    _send_email_preferring_resend(
        to_email=email,
        subject=subject,
        html=html_text,
        plain_text=plain_text,
    )

def send_email_via_resend(
    *,
    to_email: str,
    subject: str,
    html: str,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise RuntimeError("Resend is not configured")

    resend.api_key = settings.resend_api_key
    payload: dict = {
        "from": settings.resend_from_email,
        "to": to_email,
        "subject": subject,
        "html": html,
    }
    if attachments:
        # Resend expects {"filename": ..., "content": <base64-or-bytes>, "content_type": ...}
        import base64

        payload["attachments"] = [
            {
                "filename": filename,
                "content": base64.b64encode(content).decode("ascii"),
                "content_type": content_type,
            }
            for filename, content, content_type in attachments
        ]
    logger.info(
        "Resend: sending email from=%s to=%s subject=%r has_attachments=%s",
        settings.resend_from_email,
        to_email,
        subject,
        bool(attachments),
    )
    response = resend.Emails.send(payload)
    logger.info("Resend: API response = %r", response)
    if not response:
        raise RuntimeError("Resend send failed (empty response)")
    if isinstance(response, dict) and response.get("error"):
        raise RuntimeError(f"Resend send failed: {response['error']}")


def send_email_via_smtp(
    *,
    to_email: str,
    subject: str,
    html: str,
    plain_text: str | None = None,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
) -> None:
    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password or not settings.smtp_from_email:
        raise RuntimeError("SMTP is not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email

    if plain_text:
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    for attachment in attachments or []:
        filename, content, content_type = attachment
        maintype, subtype = (
            content_type.split("/", 1) if "/" in content_type else ("application", "octet-stream")
        )
        part = MIMEBase(maintype, subtype)
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
