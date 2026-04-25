import resend

from app.core.config import get_settings


def send_registration_code_email(email: str, code: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise RuntimeError("Resend is not configured")

    resend.api_key = settings.resend_api_key

    subject = "Your verification code"
    html_text = (
        "<p>Your verification code is:</p>"
        f"<h2>{code}</h2>"
        f"<p>This code expires in {settings.email_verification_code_ttl_minutes} minutes.</p>"
    )

    response = resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": email,
            "subject": subject,
            "html": html_text,
        }
    )

    if not response:
        raise RuntimeError("Resend send failed")


def send_password_reset_code_email(email: str, code: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise RuntimeError("Resend is not configured")

    resend.api_key = settings.resend_api_key

    subject = "Your password reset code"
    html_text = (
        "<p>Your password reset code is:</p>"
        f"<h2>{code}</h2>"
        f"<p>This code expires in {settings.email_verification_code_ttl_minutes} minutes.</p>"
    )

    response = resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": email,
            "subject": subject,
            "html": html_text,
        }
    )

    if not response:
        raise RuntimeError("Resend send failed")
