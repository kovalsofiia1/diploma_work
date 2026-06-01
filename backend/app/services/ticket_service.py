from __future__ import annotations

import hashlib
import os
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import get_settings
from app.services import blockchain_service
from app.services.qr_service import decode_ticket_qr_token, generate_ticket_qr_token
from app.services.email_service import send_email
from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.models.checkin import Checkin
from app.models.user import User
from app.models.event import Event


def _compute_ticket_hash(ticket_id: str) -> str:
    """
    README-conformant hash:
    sha256(f"{ticket_id}{SECRET_KEY}")
    Returns 0x-prefixed hex string suitable for bytes32.
    """
    settings = get_settings()
    payload = f"{ticket_id}{settings.ticket_secret_key}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return "0x" + digest


def book_ticket(
    db: Session,
    *,
    event_id: int,
    user_id: int,
    quantity: int = 1,
    seat: Optional[str] = None,
    seat_id: Optional[str] = None,
    attendee_name: Optional[str] = None,
    price_amount: Optional[int] = None,
    price_currency: Optional[str] = None,
) -> tuple[Ticket, dict]:
    now = datetime.now(timezone.utc)
    ticket_id = uuid4().hex
    code = f"TKT-{ticket_id[:10].upper()}"
    ticket_hash = _compute_ticket_hash(ticket_id)

    ticket = Ticket(
        ticket_id=ticket_id,
        code=code,
        event_id=event_id,
        user_id=user_id,
        quantity=quantity,
        seat_id=seat_id,
        seat=seat,
        attendee_name=attendee_name,
        token_id=None,
        price_amount=price_amount,
        price_currency=price_currency,
        ticket_hash=ticket_hash,
        status="pending_onchain",
        used=False,
        created_at=now.replace(tzinfo=None),
        updated_at=now.replace(tzinfo=None),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Use DB id as token_id for chain
    token_id = ticket.id
    ticket.token_id = token_id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    qr_token = generate_ticket_qr_token(ticket_id=ticket.id, event_id=ticket.event_id)
    qr = {"qr_token": qr_token, "ticket_id": ticket.ticket_id}
    return ticket, qr


def mint_ticket_async(ticket_id: int) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        if ticket.status not in ("pending_onchain", "reserved"):
            return

        token_id = ticket.token_id or ticket.id
        tx_hash = blockchain_service.mint_ticket(
            token_id=token_id,
            event_id=ticket.event_id,
            seat_id=ticket.seat_id,
            ticket_hash=ticket.ticket_hash,
        )
        ticket.tx_hash = tx_hash
        ticket.status = "confirmed_onchain"
        db.add(ticket)
        db.commit()
    except Exception:
        if "ticket" in locals() and ticket:
            ticket.status = "failed_onchain"
            db.add(ticket)
            db.commit()
    finally:
        db.close()


def verify_ticket_qr(db: Session, *, qr_token: str) -> tuple[bool, Optional[str], Optional[Ticket]]:
    try:
        payload = decode_ticket_qr_token(qr_token)
    except ValueError as exc:
        return False, str(exc), None

    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == payload["ticket_id"], Ticket.event_id == payload["event_id"])
        .first()
    )
    if not ticket:
        return False, "Ticket not found", None
    if ticket.used:
        return False, "Already used", ticket
    if ticket.status == "failed_onchain":
        return False, "On-chain confirmation failed", ticket
    return True, None, ticket


def checkin_ticket(db: Session, *, qr_token: str, staff_user_id: Optional[int]) -> tuple[bool, Optional[str], Optional[Ticket]]:
    ok, reason, ticket = verify_ticket_qr(db, qr_token=qr_token)
    if not ok or not ticket:
        return False, reason, ticket

    ticket.used = True
    ticket.status = "used"
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    ch = Checkin(ticket_id=ticket.id, staff_user_id=staff_user_id)
    db.add(ch)
    db.commit()

    return True, None, ticket


def mark_ticket_used_async(ticket_id: int) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        tx_hash = blockchain_service.mark_used(ticket.token_id or ticket.id)
        ticket.tx_hash = tx_hash
        db.add(ticket)
        db.commit()
    except Exception:
        return
    finally:
        db.close()


def _register_pdf_fonts() -> tuple[str, str]:
    """
    Registers Unicode-capable fonts for Cyrillic text in PDFs.
    Returns (regular_font_name, bold_font_name).
    """
    regular_name = "Helvetica"
    bold_name = "Helvetica-Bold"

    candidates = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]

    for regular_path, bold_path in candidates:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            try:
                if "TicketSans" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("TicketSans", regular_path))
                if "TicketSansBold" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("TicketSansBold", bold_path))
                return "TicketSans", "TicketSansBold"
            except Exception:
                continue

    return regular_name, bold_name


def _draw_info_row(
    c: canvas.Canvas,
    *,
    x: float,
    y: float,
    label: str,
    value: str,
    regular_font: str,
    bold_font: str,
) -> float:
    c.setFont(bold_font, 10)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawString(x, y, label)
    c.setFont(regular_font, 10)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(x + 135, y, value)
    return y - 18


def _build_ticket_pdf(ticket: Ticket, event: Event, qr_token: str) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    regular_font, bold_font = _register_pdf_fonts()

    # Page card
    margin = 32
    card_x = margin
    card_y = 80
    card_w = width - margin * 2
    card_h = height - 140
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.roundRect(card_x, card_y, card_w, card_h, 14, fill=1, stroke=1)

    # Header band
    header_h = 70
    c.setFillColor(colors.HexColor("#0F766E"))
    c.roundRect(card_x, card_y + card_h - header_h, card_w, header_h, 14, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(bold_font, 20)
    c.drawString(card_x + 20, card_y + card_h - 42, "Квиток на подію")
    c.setFont(regular_font, 10)
    c.drawString(card_x + 20, card_y + card_h - 58, "Електронний квиток для проходу на захід")

    # Ticket badge
    badge_w = 170
    badge_h = 28
    badge_x = card_x + card_w - badge_w - 18
    badge_y = card_y + card_h - 52
    c.setFillColor(colors.HexColor("#115E59"))
    c.roundRect(badge_x, badge_y, badge_w, badge_h, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(bold_font, 11)
    c.drawCentredString(badge_x + badge_w / 2, badge_y + 9, ticket.code)

    # Details section
    details_x = card_x + 22
    details_y = card_y + card_h - header_h - 28
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont(bold_font, 13)
    c.drawString(details_x, details_y, "Деталі квитка")
    y = details_y - 20

    event_date = (
        event.startDate.strftime("%d.%m.%Y %H:%M")
        if event.startDate
        else "-"
    )
    y = _draw_info_row(c, x=details_x, y=y, label="Назва події:", value=event.name or "-", regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Дата і час:", value=event_date, regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Локація:", value=event.location_name or "-", regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Місто:", value=event.city or "-", regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Місце:", value=ticket.seat or ticket.seat_id or "-", regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Відвідувач:", value=ticket.attendee_name or "-", regular_font=regular_font, bold_font=bold_font)
    price_label = (
        f"{ticket.price_amount} {ticket.price_currency or ''}".strip()
        if ticket.price_amount is not None
        else "-"
    )
    y = _draw_info_row(c, x=details_x, y=y, label="Ціна:", value=price_label, regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Кількість:", value=str(ticket.quantity), regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Статус:", value=ticket.status, regular_font=regular_font, bold_font=bold_font)
    y = _draw_info_row(c, x=details_x, y=y, label="Ticket ID:", value=ticket.ticket_id, regular_font=regular_font, bold_font=bold_font)

    # QR section
    qr_img = qrcode.make(qr_token)
    qr_buf = BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)

    qr_box_w = 200
    qr_box_h = 240
    qr_box_x = card_x + card_w - qr_box_w - 22
    qr_box_y = card_y + 120
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.roundRect(qr_box_x, qr_box_y, qr_box_w, qr_box_h, 10, fill=1, stroke=1)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont(bold_font, 12)
    c.drawCentredString(qr_box_x + qr_box_w / 2, qr_box_y + qr_box_h - 22, "QR для check-in")
    c.drawImage(
        qr_reader,
        qr_box_x + 25,
        qr_box_y + 50,
        width=150,
        height=150,
        preserveAspectRatio=True,
        mask="auto",
    )
    c.setFont(regular_font, 9)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawCentredString(qr_box_x + qr_box_w / 2, qr_box_y + 32, "Покажіть цей QR при вході")
    c.drawCentredString(qr_box_x + qr_box_w / 2, qr_box_y + 18, "Скриншот або друкований PDF")

    # Footer note
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont(regular_font, 8)
    c.drawString(card_x + 22, card_y + 18, "Квиток сформовано автоматично. Не передавайте QR третім особам.")

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def send_ticket_pdf_email_async(ticket_id: int) -> None:
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return
        user = db.query(User).filter(User.id == ticket.user_id).first()
        event = db.query(Event).filter(Event.id == ticket.event_id).first()
        if not user or not user.email or not event:
            return

        qr_token = generate_ticket_qr_token(ticket_id=ticket.id, event_id=ticket.event_id)
        pdf_content = _build_ticket_pdf(ticket, event, qr_token)

        subject = f"Your ticket for {event.name}"
        html = (
            f"<p>Hello,</p>"
            f"<p>Your ticket <strong>{ticket.code}</strong> is attached as PDF.</p>"
            f"<p>Event: <strong>{event.name}</strong></p>"
            f"<p>Date: {event.startDate.isoformat() if event.startDate else '-'}</p>"
            f"<p>Location: {event.location_name or '-'}, {event.city or '-'}</p>"
            "<p>Please present the QR code from the PDF during check-in.</p>"
        )
        plain = (
            f"Your ticket {ticket.code} is attached.\n"
            f"Event: {event.name}\n"
            f"Date: {event.startDate.isoformat() if event.startDate else '-'}\n"
            f"Location: {event.location_name or '-'}, {event.city or '-'}\n"
        )
        send_email(
            to_email=user.email,
            subject=subject,
            html=html,
            plain_text=plain,
            attachments=[(f"ticket-{ticket.code}.pdf", pdf_content, "application/pdf")],
        )
    except Exception:
        return
    finally:
        db.close()


