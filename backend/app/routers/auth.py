from typing import Optional
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User, AuthProvider, UserCity
from app.models.email_verification import EmailVerificationCode
from app.models.event import Event, CityActivityLog, CityActivityType
from app.models.ticket import Ticket
from app.services.email_service import send_registration_code_email, send_password_reset_code_email, send_email_via_smtp
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserOut,
    Token,
    GoogleAuthStartResponse,
    UserUpdate,
    UserCitiesRequest,
    UserCitiesResponse,
    UserProfileStatsOut,
    RegisterVerificationSendRequest,
    RegisterVerificationSendResponse,
    PasswordResetSendCodeRequest,
    PasswordResetConfirmRequest,
    PasswordResetResponse,
    SmtpEmailSendRequest,
    SmtpEmailSendResponse,
)

router = APIRouter()
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, *, email: str, password: Optional[str], full_name: Optional[str], provider: AuthProvider, provider_id: Optional[str]) -> User:
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=get_password_hash(password) if password else None,
        provider=provider,
        provider_id=provider_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _make_verification_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_verification_code(email: str, code: str) -> str:
    payload = f"{email.strip().lower()}:{code}:{settings.email_verification_secret}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _verify_code(db: Session, email: str, code: str, purpose: str) -> bool:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    code_hash = _hash_verification_code(email, code)
    rec = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == purpose,
            EmailVerificationCode.code_hash == code_hash,
            EmailVerificationCode.used.is_(False),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )
    if not rec:
        return False
    rec.used = True
    db.add(rec)
    db.commit()
    return True


@router.post("/register/send-code", response_model=RegisterVerificationSendResponse)
def send_registration_code(payload: RegisterVerificationSendRequest, db: Session = Depends(get_db)) -> RegisterVerificationSendResponse:
    email = str(payload.email).strip().lower()
    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == "register",
        EmailVerificationCode.used.is_(False),
    ).update({EmailVerificationCode.used: True}, synchronize_session=False)

    code = _make_verification_code()
    rec = EmailVerificationCode(
        email=email,
        purpose="register",
        code_hash=_hash_verification_code(email, code),
        expires_at=(now + timedelta(minutes=settings.email_verification_code_ttl_minutes)),
        used=False,
    )
    db.add(rec)
    db.commit()

    try:
        send_registration_code_email(email, code)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send verification code: {exc}")

    return RegisterVerificationSendResponse(message="Verification code sent")


@router.post("/email/send-smtp", response_model=SmtpEmailSendResponse)
def send_email_smtp(payload: SmtpEmailSendRequest) -> SmtpEmailSendResponse:
    try:
        send_email_via_smtp(
            to_email=str(payload.to_email),
            subject=payload.subject,
            html=payload.html,
            plain_text=payload.plain_text,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SMTP send failed: {exc}")

    return SmtpEmailSendResponse(message="Email sent via SMTP")


async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.get_unverified_claims(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(sub)).first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Token:
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if not _verify_code(db, str(user_in.email), user_in.verification_code, purpose="register"):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    user = create_user(
        db,
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        provider=AuthProvider.local,
        provider_id=None,
    )
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.post("/password/send-code", response_model=PasswordResetResponse)
def send_password_reset_code(payload: PasswordResetSendCodeRequest, db: Session = Depends(get_db)) -> PasswordResetResponse:
    email = str(payload.email).strip().lower()
    user = get_user_by_email(db, email)
    # Do not leak if email exists
    if not user or not user.hashed_password:
        return PasswordResetResponse(message="If this email exists, a reset code has been sent")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == email,
        EmailVerificationCode.purpose == "reset_password",
        EmailVerificationCode.used.is_(False),
    ).update({EmailVerificationCode.used: True}, synchronize_session=False)

    code = _make_verification_code()
    rec = EmailVerificationCode(
        email=email,
        purpose="reset_password",
        code_hash=_hash_verification_code(email, code),
        expires_at=(now + timedelta(minutes=settings.email_verification_code_ttl_minutes)),
        used=False,
    )
    db.add(rec)
    db.commit()

    try:
        send_password_reset_code_email(email, code)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send reset code: {exc}")

    return PasswordResetResponse(message="If this email exists, a reset code has been sent")


@router.post("/password/reset", response_model=PasswordResetResponse)
def reset_password(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> PasswordResetResponse:
    email = str(payload.email).strip().lower()
    user = get_user_by_email(db, email)
    if not user or not user.hashed_password:
        raise HTTPException(status_code=400, detail="Invalid email or reset code")

    if not _verify_code(db, email, payload.code, purpose="reset_password"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    return PasswordResetResponse(message="Password updated successfully")


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        date_of_birth=current_user.date_of_birth,
        description=current_user.description,
        image_url=current_user.image_url,
        is_active=current_user.is_active,
        status=current_user.status,  # type: ignore[arg-type]
    )


@router.patch("/me", response_model=UserOut)
def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserOut:
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserOut(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        date_of_birth=current_user.date_of_birth,
        description=current_user.description,
        image_url=current_user.image_url,
        is_active=current_user.is_active,
        status=current_user.status,  # type: ignore[arg-type]
    )


@router.post("/me/image", response_model=UserOut)
def upload_profile_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserOut:
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
        
    try:
        from app.utils.cloudinary import upload_image
        image_url = upload_image(file, folder=f"users/{current_user.id}")
        
        current_user.image_url = image_url
        db.commit()
        db.refresh(current_user)
        
        return UserOut(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            date_of_birth=current_user.date_of_birth,
            description=current_user.description,
            image_url=current_user.image_url,
            is_active=current_user.is_active,
            status=current_user.status,  # type: ignore[arg-type]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.get("/me/cities", response_model=UserCitiesResponse)
def get_my_cities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserCitiesResponse:
    cities = db.query(UserCity.city).filter(UserCity.user_id == current_user.id).all()
    return UserCitiesResponse(cities=[c[0] for c in cities])


@router.post("/me/cities", response_model=UserCitiesResponse)
def update_my_cities(
    req: UserCitiesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> UserCitiesResponse:
    # Delete existing cities for this user
    db.query(UserCity).filter(UserCity.user_id == current_user.id).delete()
    
    # Add new cities
    unique_cities = list(set(req.cities))
    for city in unique_cities:
        db.add(UserCity(user_id=current_user.id, city=city))
        city_name = city.strip()
        if city_name:
            db.add(
                CityActivityLog(
                    city=city_name,
                    activity_type=CityActivityType.subscription,
                )
            )
        
    db.commit()
    return UserCitiesResponse(cities=unique_cities)


@router.get("/me/stats", response_model=UserProfileStatsOut)
def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileStatsOut:
    created_events = (
        db.query(func.count(Event.id))
        .filter(
            Event.created_by_user_id == current_user.id,
            Event.source_type == "INTERNAL",
        )
        .scalar()
    ) or 0

    visited_events = (
        db.query(func.count(func.distinct(Ticket.event_id)))
        .filter(
            Ticket.user_id == current_user.id,
            Ticket.used.is_(True),
            Ticket.status != "failed",
        )
        .scalar()
    ) or 0

    purchased_tickets = (
        db.query(func.coalesce(func.sum(Ticket.quantity), 0))
        .filter(
            Ticket.user_id == current_user.id,
            Ticket.status != "failed",
        )
        .scalar()
    ) or 0

    return UserProfileStatsOut(
        created_events=int(created_events),
        visited_events=int(visited_events),
        purchased_tickets=int(purchased_tickets),
    )


@router.post("/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)) -> None:
    # Stateless JWT logout: client should discard token. Endpoint kept for symmetry and future revocation logic.
    return None


@router.get("/google/start", response_model=GoogleAuthStartResponse)
def google_start() -> GoogleAuthStartResponse:
    # Build Google OAuth2 consent screen URL
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": settings.google_scope,
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
    }
    from urllib.parse import urlencode

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return GoogleAuthStartResponse(authorization_url=url)


@router.get("/google/callback", response_model=Token)
async def google_callback(code: str, db: Session = Depends(get_db)) -> Token:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            token_url,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    token_data = resp.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No id_token in Google response")

    # Validate id_token audience via tokeninfo endpoint (simplified verification)
    async with httpx.AsyncClient(timeout=20) as client:
        info_resp = await client.get("https://oauth2.googleapis.com/tokeninfo", params={"id_token": id_token})
    if info_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid id_token")
    info = info_resp.json()
    if info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=400, detail="Invalid token audience")

    email = info.get("email")
    sub = info.get("sub")
    name = info.get("name")
    if not email or not sub:
        raise HTTPException(status_code=400, detail="Google profile missing required fields")

    user = get_user_by_email(db, email)
    if not user:
        user = create_user(
            db,
            email=email,
            password=None,
            full_name=name,
            provider=AuthProvider.google,
            provider_id=sub,
        )
    token = create_access_token(str(user.id))
    return Token(access_token=token)

