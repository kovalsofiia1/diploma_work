"""Security of the chatbot (task 3.9): rate limiting, message screening and text guards.

Layers, outermost first (see routers/chat.py and services/chat_service.py):
1. rate limit per client (`check_and_record`), before anything costs LLM tokens;
2. screening of the user's text (`normalize_message`, `looks_like_injection`), refused without an LLM call;
3. the model's own `intent` check for off-topic questions (chat_service);
4. validation of the model's filters (schemas.chat.SearchFilters);
5. guards on what the model produces and on what is sent to it (`intro_is_safe`, `text_for_llm`).

The patterns below are a heuristic first line of defence, not a proof: the model has no tools and the
cards in the reply always come from the DB, so even a successful injection can only change wording.
"""
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.chat import ChatRequestLog

WINDOW = timedelta(hours=1)
CLEANUP_AFTER = timedelta(hours=2)
MAX_INTRO_CHARS = 300


# ---------------------------------------------------------------- rate limit

class RateLimited(Exception):
    def __init__(self, retry_after_seconds: int, scope: str):
        super().__init__(f"rate limited ({scope}), retry in {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds
        self.scope = scope  # "client" | "global"


@dataclass(frozen=True)
class RateLimitState:
    limit: int
    remaining: int


def client_key(request: Request) -> str:
    """`user:<id>` for a Bearer token with a valid signature, else `ip:<address>`.

    The signature is verified here on purpose (the router's helper reads claims without verifying):
    a forged token must not be able to pick, borrow or multiply buckets.
    """
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() == "bearer" and token:
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            sub = payload.get("sub")
            if sub is not None and str(sub).isdigit():
                return f"user:{int(sub)}"
        except JWTError:
            pass
    forwarded = request.headers.get("x-forwarded-for", "")
    address = forwarded.split(",")[0].strip() if forwarded else ""
    if not address:
        address = request.client.host if request.client else "unknown"
    return f"ip:{address[:60]}"


def _seconds_until(oldest: Optional[datetime], now: datetime) -> int:
    if oldest is None:
        return 1
    return max(1, int((oldest + WINDOW - now).total_seconds()) + 1)


def check_and_record(db: Session, key: str, now: Optional[datetime] = None) -> RateLimitState:
    """Count the client's requests in the last hour; raise RateLimited or record this one.

    Every request that passes is recorded, refused ones included, so spamming injections still costs quota.
    """
    settings = get_settings()
    now = now or datetime.utcnow()
    window_start = now - WINDOW

    # Old rows are useless after the window; deleting them here avoids a scheduler job.
    db.query(ChatRequestLog).filter(ChatRequestLog.created_at < now - CLEANUP_AFTER).delete(synchronize_session=False)

    per_client = ChatRequestLog.client_key == key
    in_window = ChatRequestLog.created_at > window_start

    used = db.query(func.count(ChatRequestLog.id)).filter(per_client, in_window).scalar() or 0
    if used >= settings.chat_rate_limit_per_hour:
        oldest = db.query(func.min(ChatRequestLog.created_at)).filter(per_client, in_window).scalar()
        db.commit()
        raise RateLimited(_seconds_until(oldest, now), "client")

    total = db.query(func.count(ChatRequestLog.id)).filter(in_window).scalar() or 0
    if total >= settings.chat_global_limit_per_hour:
        oldest = db.query(func.min(ChatRequestLog.created_at)).filter(in_window).scalar()
        db.commit()
        raise RateLimited(_seconds_until(oldest, now), "global")

    db.add(ChatRequestLog(client_key=key, created_at=now))
    db.commit()
    return RateLimitState(limit=settings.chat_rate_limit_per_hour, remaining=settings.chat_rate_limit_per_hour - used - 1)


# ---------------------------------------------------------------- text screening

_INVISIBLE = dict.fromkeys(map(ord, "​‌‍⁠﻿­᠎"), None)


def normalize_message(text: str) -> str:
    """NFKC-normalise, drop control and zero-width characters, collapse whitespace."""
    value = unicodedata.normalize("NFKC", text or "").translate(_INVISIBLE)
    value = "".join(ch for ch in value if ch in "\n\t " or not unicodedata.category(ch).startswith("C"))
    return re.sub(r"\s+", " ", value).strip()


_PHRASES = [
    # English
    r"ignore\s+(?:\w+\s+){0,3}?(?:instructions?|prompts?|rules?|messages?|guidelines?)",
    r"disregard\s+(?:\w+\s+){0,3}?(?:instructions?|prompts?|rules?|guidelines?)",
    r"forget\s+(?:\w+\s+){0,3}?(?:instructions?|prompts?|rules?|guidelines?)",
    r"(reveal|show|print|repeat|display|leak|output|tell\s+me)\s+(me\s+)?(your|the)\s+(system\s+|initial\s+|hidden\s+|original\s+)?(prompt|instructions?)",
    r"system\s+(prompt|message|instructions?)",
    r"developer\s+(mode|message)",
    r"\bjailbreak",
    r"(?-i:\bDAN\b)",  # case-sensitive: the name "Dan" is fine
    r"(^|[.!?;:]\s*)you\s+are\s+now\b",
    r"(pretend|act)\s+(to\s+be|as\s+if\s+you|like\s+you\s+are)",
    r"new\s+instructions\s*:",
    # Ukrainian
    r"ігноруй\w*\s+(?:\w+\s+){0,3}?(?:інструкці\w+|вказівк\w+|правил\w+|промпт\w*)",
    r"забудь\w*\s+(?:\w+\s+){0,3}?(?:інструкці\w+|вказівк\w+|правил\w+|промпт\w*)",
    r"(покажи|виведи|розкрий|повтори|скажи|надрукуй)\s+(мені\s+)?(свій|свої|системн\w+)\s+(промпт|інструкції|повідомлення)",
    r"системн\w+\s+(промпт|повідомлення|інструкці\w+)",
    r"(^|[.!?;:]\s*)ти\s+тепер\b",
    r"режим\s+розробника",
    r"(уяви|вдавай|прикинься),?\s+(що\s+)?ти\b",
    # Russian
    r"игнорируй\w*\s+(?:\w+\s+){0,3}?(?:инструкци\w+|указани\w+|правил\w+|промпт\w*)",
    r"забудь\w*\s+(?:\w+\s+){0,3}?(?:инструкци\w+|указани\w+|правил\w+|промпт\w*)",
    r"(покажи|выведи|раскрой|повтори|скажи|напечатай)\s+(мне\s+)?(свой|свои|системн\w+)\s+(промпт|инструкции|сообщение)",
    r"системн\w+\s+(промпт|сообщение|инструкци\w+)",
    r"(^|[.!?;:]\s*)ты\s+теперь\b",
    r"режим\s+разработчика",
    r"(представь|притворись),?\s+(что\s+)?ты\b",
]
_PHRASE_RE = re.compile("|".join(f"(?:{p})" for p in _PHRASES), re.IGNORECASE | re.UNICODE)

# Letters-only forms catch spaced / punctuated obfuscation ("i.g.n.o.r.e  previous instructions").
_LATIN_KEYWORDS = (
    "ignorepreviousinstructions", "ignoreallinstructions", "ignoreallpreviousinstructions",
    "ignoretheaboveinstructions", "disregardpreviousinstructions",
    "disregardallinstructions", "forgetallinstructions", "forgetyourinstructions",
    "forgetpreviousinstructions", "systemprompt", "revealyourprompt", "showyourprompt",
    "printyourprompt", "developermode", "jailbreak",
)
_CYRILLIC_KEYWORDS = (
    "ігноруйпопередніінструкції", "ігноруйвсіінструкції", "ігноруйусіінструкції",
    "забудьвсіінструкції", "забудьусіінструкції", "забудьпопередніінструкції", "системнийпромпт",
    "режимрозробника", "игнорируйпредыдущиеинструкции", "игнорируйвсеинструкции",
    "забудьвсеинструкции", "системныйпромпт", "режимразработчика",
)
# Cyrillic letters that look like Latin ones, so "ignоre" (Cyrillic о) is still caught.
_HOMOGLYPHS = str.maketrans("аеорсухіїкмнтв", "aeopcyxiikmntb")


def looks_like_injection(text: str) -> bool:
    """True for attempts to override instructions, extract the prompt or change the bot's role."""
    value = normalize_message(text)
    if not value:
        return False
    if _PHRASE_RE.search(value):
        return True
    letters = re.sub(r"[\W\d_]+", "", value.casefold())
    if any(keyword in letters for keyword in _CYRILLIC_KEYWORDS):
        return True
    latin = letters.translate(_HOMOGLYPHS)
    return any(keyword in latin for keyword in _LATIN_KEYWORDS)


# ---------------------------------------------------------------- guards around the model

_FORBIDDEN_IN_INTRO = '«»"“”<>`{}[]\\'


def intro_is_safe(intro: object) -> bool:
    """The intro is plain friendly text: no markup, links, quoted names or echoed instructions."""
    if not isinstance(intro, str) or not intro.strip() or len(intro) > MAX_INTRO_CHARS:
        return False
    lowered = intro.lower()
    if any(ch in intro for ch in _FORBIDDEN_IN_INTRO):
        return False
    if any(marker in lowered for marker in ("http", "www.", "://", "system prompt", "системн")):
        return False
    return not looks_like_injection(intro)


def text_for_llm(value: Optional[str], limit: int = 80) -> str:
    """Third-party text (event names, cities) as it may enter a prompt: cleaned, short, never an instruction."""
    cleaned = normalize_message(value or "")[:limit]
    return "Подія" if looks_like_injection(cleaned) else cleaned
