import resend
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import get_settings


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
    send_email_via_smtp(
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
    send_email_via_smtp(
        to_email=email,
        subject=subject,
        html=html_text,
        plain_text=plain_text,
    )

def send_email_via_resend(*, to_email: str, subject: str, html: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key or not settings.resend_from_email:
        raise RuntimeError("Resend is not configured")

    resend.api_key = settings.resend_api_key
    response = resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": to_email,
            "subject": subject,
            "html": html,
        }
    )
    if not response:
        raise RuntimeError("Resend send failed")


def send_email_via_smtp(*, to_email: str, subject: str, html: str, plain_text: str | None = None) -> None:
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

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
