from typing import Any, List, Optional
from datetime import datetime, timedelta
import json
import httpx
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer, or_, inspect, text, func

from app.db.session import get_db
from app.models.event import Event, City, CityScrapeState, EventUser, EventUserRole
from app.models.ticket import Ticket
from app.models.user import User, UserFavoriteEvent
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventOut,
    ExternalEventCreate,
    UnifiedEventsOut,
    UnifiedEventOut,
    EventKind,
    ScrapeRequest,
    EventMemberOut,
    EventMembersUpsertRequest,
    EventMembersUpsertResponse,
)
from app.routers.auth import get_current_user
from app.core.config import get_settings

settings = get_settings()

router = APIRouter()
CITY_SCRAPE_TTL = timedelta(hours=12)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _normalize_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized.rstrip("/")


def _city_scrape_key(city: str) -> str:
    return city.strip().casefold()


def _city_scrape_recently_updated(db: Session, city: str) -> bool:
    key = _city_scrape_key(city)
    row = db.query(CityScrapeState).filter(CityScrapeState.city_key == key).first()
    if not row or not row.last_scraped_at:
        return False
    return datetime.utcnow() - row.last_scraped_at < CITY_SCRAPE_TTL


def _mark_city_scraped_now(db: Session, city: str) -> None:
    key = _city_scrape_key(city)
    row = db.query(CityScrapeState).filter(CityScrapeState.city_key == key).first()
    if row:
        row.city_name = city.strip() or city
        row.last_scraped_at = datetime.utcnow()
        db.add(row)
    else:
        db.add(
            CityScrapeState(
                city_key=key,
                city_name=city.strip() or city,
                last_scraped_at=datetime.utcnow(),
            )
        )
    db.commit()


def _parser_base_url() -> str:
    base = settings.parser_service_url.rstrip("/")
    if base.endswith("/scrape/events"):
        return base[: -len("/scrape/events")]
    return base


def _ensure_city_name_en_column(db: Session) -> None:
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("cities")}
    if "name_en" in cols:
        return
    db.execute(text("ALTER TABLE cities ADD COLUMN name_en VARCHAR(255)"))
    db.commit()


async def _fetch_parser_cities() -> list[dict[str, Optional[str]]]:
    parser_cities_url = f"{_parser_base_url()}/cities"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(parser_cities_url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error communicating with parser-service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Parser service returned an error: {e.response.text}")

    if not isinstance(data, dict):
        return []

    items_raw = data.get("city_items", [])
    out: list[dict[str, Optional[str]]] = []
    if isinstance(items_raw, list):
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            name_en_raw = item.get("name_en")
            name_en = str(name_en_raw).strip() if isinstance(name_en_raw, str) and name_en_raw.strip() else None
            out.append({"name": name, "name_en": name_en})

    if out:
        return out

    # Backward-compatible fallback when parser-service returns only `cities`.
    raw_names = data.get("cities", [])
    if not isinstance(raw_names, list):
        return []
    for item in raw_names:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if name:
            out.append({"name": name, "name_en": None})
    return out


def _apply_search_filter(query, search: Optional[str]):
    term = (search or "").strip()
    if not term:
        return query

    pattern = f"%{term}%"
    return query.filter(
        or_(
            Event.name.ilike(pattern),
            Event.city.ilike(pattern),
            Event.location_name.ilike(pattern),
            Event.description.ilike(pattern),
            Event.event_type.ilike(pattern),
            Event.source_name.ilike(pattern),
        )
    )


def _booked_places_for_event(db: Session, event_id: int) -> int:
    booked = (
        db.query(func.coalesce(func.sum(Ticket.quantity), 0))
        .filter(Ticket.event_id == event_id, Ticket.status != "failed")
        .scalar()
    )
    return int(booked or 0)


def _to_out(
    e: Event,
    *,
    is_saved: bool = False,
    can_edit: bool = False,
    booked_places: Optional[int] = None,
) -> EventOut:
    total_places = e.total_places
    booked = None
    available = None
    if total_places is not None:
        booked = max(0, int(booked_places or 0))
        available = max(total_places - booked, 0)

    return EventOut(
        id=e.id,
        uid=e.uid,
        name=e.name,
        type=e.event_type,
        url=e.source_url,
        order_url=e.order_url,
        startDate=e.startDate.isoformat() if isinstance(e.startDate, datetime) and e.startDate else None,
        endDate=e.endDate.isoformat() if isinstance(e.endDate, datetime) and e.endDate else None,
        location_name=e.location_name,
        city=e.city,
        price_low=e.price_low,
        price_high=e.price_high,
        price_currency=e.price_currency,
        image=e.image,
        source=e.source_name or "platform",
        verified=e.is_verified,
        description=e.description,
        additional=e.additional,
        total_places=total_places,
        booked_places=booked,
        available_places=available,
        isSaved=is_saved,
        can_edit=can_edit,
    )


def _roles_map_for_user(db: Session, user: Optional[User], event_ids: List[int]) -> dict[int, EventUserRole]:
    if not user or not event_ids:
        return {}
    rows = (
        db.query(EventUser.event_id, EventUser.role)
        .filter(EventUser.user_id == user.id, EventUser.event_id.in_(event_ids))
        .all()
    )
    return {int(event_id): role for event_id, role in rows}


def _can_edit_event(e: Event, user: Optional[User], roles: dict[int, EventUserRole]) -> bool:
    if not user:
        return False
    if e.created_by_user_id == user.id:
        return True
    return roles.get(e.id) == EventUserRole.organizer


def _has_event_access(e: Event, user: Optional[User], roles: dict[int, EventUserRole]) -> bool:
    if not user:
        return False
    if e.created_by_user_id == user.id:
        return True
    return roles.get(e.id) in (EventUserRole.organizer, EventUserRole.scanner)


def _to_unified_out(e: Event, *, is_saved: bool = False) -> UnifiedEventOut:
    base = _to_out(e, is_saved=is_saved)
    return UnifiedEventOut(
        **base.model_dump(exclude={"uid"}),
        kind=EventKind.internal if e.source_type == "INTERNAL" else EventKind.external,
        uid=base.uid or (f"internal:{e.id}" if e.source_type == "INTERNAL" else f"external:{e.id}"),
    )


def _find_event_by_uid(db: Session, uid: str) -> Optional[Event]:
    obj = db.query(Event).filter(Event.uid == uid).first()
    if obj:
        return obj
    if ":" in uid:
        _, raw_id = uid.split(":", 1)
        if raw_id.isdigit():
            return db.query(Event).filter(Event.id == int(raw_id)).first()
    return None


def _get_optional_current_user(db: Session, request: Request) -> Optional[User]:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header:
        return None
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    try:
        payload = jwt.get_unverified_claims(token)
        sub = payload.get("sub")
        if not sub:
            return None
        user_id = int(sub)
    except (JWTError, ValueError, TypeError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def _is_event_saved_for_user(db: Session, user: Optional[User], event_id: int) -> bool:
    if not user:
        return False
    return (
        db.query(UserFavoriteEvent)
        .filter(
            UserFavoriteEvent.user_id == user.id,
            UserFavoriteEvent.event_id == event_id,
        )
        .first()
        is not None
    )


def _event_matches_filters(
    e: Event,
    *,
    search: Optional[str],
    city: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    min_price: Optional[int],
    max_price: Optional[int],
    event_type: Optional[str],
) -> bool:
    if city and city.lower() not in (e.city or "").lower():
        return False

    if start_date and (e.startDate is None or e.startDate < start_date):
        return False

    if end_date and (e.startDate is None or e.startDate > end_date):
        return False

    if event_type and event_type.lower() not in (e.event_type or "").lower():
        return False

    term = (search or "").strip().lower()
    if term:
        haystack = " ".join(
            [
                e.name or "",
                e.city or "",
                e.location_name or "",
                e.description or "",
                e.event_type or "",
                e.source_name or "",
            ]
        ).lower()
        if term not in haystack:
            return False

    if min_price is not None or max_price is not None:
        try:
            price = int(e.price_low) if e.price_low else None
        except (ValueError, TypeError):
            price = None

        if price is None:
            return False
        if min_price is not None and price < min_price:
            return False
        if max_price is not None and price > max_price:
            return False

    return True


def _unified_start_date_sort_key(item: UnifiedEventOut) -> tuple[int, datetime, str]:
    parsed = _parse_dt(item.startDate) if item.startDate else None
    if parsed is None:
        return (1, datetime.max, item.uid)
    return (0, parsed, item.uid)


async def _fetch_scraped_items(req: ScrapeRequest) -> list[dict[str, Any]]:
    parser_service_url = settings.parser_service_url
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                parser_service_url,
                json=req.model_dump(),
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error communicating with parser-service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Parser service returned an error: {e.response.text}")

    items = data.get("items", [])
    if not isinstance(items, list):
        return []
    return items


def _upsert_scraped_items(db: Session, scraped_items: list[dict[str, Any]]) -> tuple[list[Event], list[Event]]:
    # 1. In-memory deduplication (remove duplicates from the scraped batch itself)
    unique_items: list[dict[str, Any]] = []
    seen_keys = set()

    for item in scraped_items:
        source = item.get("source")
        url = item.get("url")
        name = item.get("name")
        start_date = item.get("startDate")

        # Use URL as the primary unique key, fallback to source+name+date
        key = (source, url) if url else (source, name, start_date)
        if key in seen_keys:
            continue

        seen_keys.add(key)
        unique_items.append(item)

    # 2. DB deduplication (check which ones are already in the database)
    urls_to_check = [_normalize_url(item.get("url")) for item in unique_items if item.get("url")]
    urls_to_check = [u for u in urls_to_check if u]
    existing_events_by_url: dict[str, Event] = {}

    if urls_to_check:
        existing_records = db.query(Event).filter(Event.source_url.in_(urls_to_check)).all()
        existing_events_by_url = {
            _normalize_url(r.source_url): r for r in existing_records if _normalize_url(r.source_url)
        }

    new_events: list[Event] = []
    updated_events: list[Event] = []

    for item in unique_items:
        raw_url = item.get("url")
        normalized_url = _normalize_url(raw_url)

        parsed_name = item.get("name")[:255] if item.get("name") else "Unknown Event"
        parsed_start = _parse_dt(item.get("startDate"))
        parsed_end = _parse_dt(item.get("endDate"))
        parsed_loc = item.get("location_name")[:255] if item.get("location_name") else None
        parsed_city = item.get("city")[:255] if item.get("city") else None
        parsed_source = item.get("source")[:64] if item.get("source") else None
        parsed_price_low = item.get("price_low")[:32] if item.get("price_low") else None
        parsed_price_high = item.get("price_high")[:32] if item.get("price_high") else None
        parsed_price_cur = item.get("price_currency")[:16] if item.get("price_currency") else None
        parsed_image = item.get("image")[:1024] if item.get("image") else None
        parsed_type = item.get("type")[:128] if item.get("type") else None
        parsed_order_url = item.get("order_url")[:1024] if item.get("order_url") else None
        parsed_desc = item.get("description")

        # Skip if URL already exists in DB
        if normalized_url and normalized_url in existing_events_by_url:
            existing = existing_events_by_url[normalized_url]
            changed = False

            if existing.name != parsed_name:
                existing.name = parsed_name
                changed = True
            if existing.startDate != parsed_start:
                existing.startDate = parsed_start
                changed = True
            if existing.endDate != parsed_end:
                existing.endDate = parsed_end
                changed = True
            if existing.location_name != parsed_loc:
                existing.location_name = parsed_loc
                changed = True
            if existing.city != parsed_city:
                existing.city = parsed_city
                changed = True
            if existing.price_low != parsed_price_low:
                existing.price_low = parsed_price_low
                changed = True
            if existing.price_high != parsed_price_high:
                existing.price_high = parsed_price_high
                changed = True
            if existing.price_currency != parsed_price_cur:
                existing.price_currency = parsed_price_cur
                changed = True
            if existing.image != parsed_image:
                existing.image = parsed_image
                changed = True
            if existing.event_type != parsed_type:
                existing.event_type = parsed_type
                changed = True
            if existing.order_url != parsed_order_url:
                existing.order_url = parsed_order_url
                changed = True
            if existing.description != parsed_desc:
                existing.description = parsed_desc
                changed = True

            if changed:
                updated_events.append(existing)
            continue

        # Fallback query by source + name + date even when URL changed/missing.
        existing = db.query(Event).filter(
            Event.source_name == parsed_source,
            Event.name == parsed_name,
            Event.startDate == parsed_start
        ).first()
        if existing:
            changed = False
            if normalized_url and _normalize_url(existing.source_url) != normalized_url:
                existing.source_url = normalized_url
                changed = True
            if existing.location_name != parsed_loc:
                existing.location_name = parsed_loc
                changed = True
            if existing.city != parsed_city:
                existing.city = parsed_city
                changed = True
            if existing.price_low != parsed_price_low:
                existing.price_low = parsed_price_low
                changed = True
            if existing.price_high != parsed_price_high:
                existing.price_high = parsed_price_high
                changed = True
            if existing.price_currency != parsed_price_cur:
                existing.price_currency = parsed_price_cur
                changed = True
            if existing.image != parsed_image:
                existing.image = parsed_image
                changed = True
            if existing.event_type != parsed_type:
                existing.event_type = parsed_type
                changed = True
            if existing.order_url != parsed_order_url:
                existing.order_url = parsed_order_url
                changed = True
            if existing.description != parsed_desc:
                existing.description = parsed_desc
                changed = True

            if changed:
                updated_events.append(existing)
            continue

        # 3. Create new Event
        obj = Event(
            name=parsed_name,
            startDate=parsed_start,
            endDate=parsed_end,
            location_name=parsed_loc,
            city=parsed_city,
            source_type="EXTERNAL",
            source_name=parsed_source,
            source_url=normalized_url[:1024] if normalized_url else None,
            is_verified=True,
            price_low=parsed_price_low,
            price_high=parsed_price_high,
            price_currency=parsed_price_cur,
            image=parsed_image,
            event_type=parsed_type,
            order_url=parsed_order_url,
            description=parsed_desc,
        )
        db.add(obj)
        new_events.append(obj)

    # 4. Save to DB and assign UIDs
    if new_events or updated_events:
        db.commit()
        for obj in new_events:
            db.refresh(obj)
            if not obj.uid:
                obj.uid = f"external:{obj.id}"
        if new_events:
            db.commit()

    return new_events, updated_events


@router.get("/cities", response_model=List[str])
def list_cities(db: Session = Depends(get_db)) -> List[str]:
    """
    Returns a list of cities from the cities table.
    """
    cities = db.query(City.name).order_by(City.name).all()
    city_list = [c[0] for c in cities]
    
    # Ensure Online is always present if table is empty
    if not city_list or "Online" not in city_list:
        city_list.append("Online")
        
    return sorted(city_list)


@router.post("/cities/sync", status_code=200)
async def sync_cities_from_parser(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _ensure_city_name_en_column(db)
    parser_city_items = await _fetch_parser_cities()
    internal_city_rows = (
        db.query(Event.city)
        .filter(Event.source_type == "INTERNAL", Event.city.isnot(None))
        .all()
    )
    internal_cities = [str(row[0]).strip() for row in internal_city_rows if row and row[0] and str(row[0]).strip()]

    city_map: dict[str, Optional[str]] = {}
    for item in parser_city_items:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        name_en = (item.get("name_en") or "").strip() or None
        if name not in city_map or (name_en and not city_map[name]):
            city_map[name] = name_en

    for city in internal_cities:
        city_map.setdefault(city, None)
    city_map.setdefault("Online", None)

    old_count = db.query(City).count()
    db.query(City).delete(synchronize_session=False)
    for name in sorted(city_map.keys()):
        db.add(City(name=name, name_en=city_map.get(name)))
    db.commit()

    return {
        "ok": True,
        "requested_by_user_id": user.id,
        "deleted": old_count,
        "inserted": len(city_map),
        "total": len(city_map),
        "from_live_sources": len({(item.get("name") or "").strip() for item in parser_city_items if (item.get("name") or "").strip()}),
        "from_internal_events": len(set(internal_cities)),
        "with_english_name": len([v for v in city_map.values() if v]),
    }


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(
    name: str = Form(..., min_length=1),
    type: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    order_url: Optional[str] = Form(None),
    startDate: Optional[str] = Form(None),
    endDate: Optional[str] = Form(None),
    location_name: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    price_low: Optional[str] = Form(None),
    price_high: Optional[str] = Form(None),
    price_currency: Optional[str] = Form(None),
    source: Optional[str] = Form("internal"),
    verified: Optional[bool] = Form(True),
    description: Optional[str] = Form(None),
    additional: Optional[str] = Form(None),
    total_places: Optional[int] = Form(None, ge=1),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db), 
    user: User = Depends(get_current_user)
) -> EventOut:
    if total_places is None:
        raise HTTPException(status_code=400, detail="total_places is required")

    image_url = None
    if image and image.filename:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        try:
            from app.utils.cloudinary import upload_image
            image_url = upload_image(image, folder="events")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")

    obj = Event(
        name=name,
        startDate=_parse_dt(startDate),
        endDate=_parse_dt(endDate),
        location_name=location_name,
        city=city,
        event_type=type,
        price_low=price_low,
        price_high=price_high,
        price_currency=price_currency,
        order_url=order_url,
        image=image_url,
        # unified fields
        source_type="INTERNAL",
        source_name=source or "platform",
        source_event_id=None,
        source_url=url,
        is_verified=True if verified is None else verified,
        created_by_user_id=user.id,
        description=description,
        additional=additional,
        total_places=total_places,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # Creator becomes organizer by default for internal events
    try:
        db.add(EventUser(event_id=obj.id, user_id=user.id, role=EventUserRole.organizer))
        db.commit()
    except Exception:
        db.rollback()

    if not obj.uid:
        obj.uid = f"internal:{obj.id}"
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return _to_out(obj, can_edit=True, booked_places=0)

@router.put("/events/{event_id}", response_model=EventOut)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EventOut:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    roles = _roles_map_for_user(db, user, [obj.id])
    if not _can_edit_event(obj, user, roles):
        raise HTTPException(status_code=403, detail="Not allowed")
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"]:
        obj.name = updates["name"]
    if "startDate" in updates:
        obj.startDate = _parse_dt(updates["startDate"])
    if "endDate" in updates:
        obj.endDate = _parse_dt(updates["endDate"])
    if "location_name" in updates:
        obj.location_name = updates["location_name"]
    if "city" in updates:
        obj.city = updates["city"]
    if "url" in updates:
        obj.source_url = updates["url"]
    if "description" in updates:
        obj.description = updates["description"]
    if "image" in updates:
        obj.image = updates["image"]
    if "price_low" in updates:
        obj.price_low = updates["price_low"]
    if "price_high" in updates:
        obj.price_high = updates["price_high"]
    if "order_url" in updates:
        obj.order_url = updates["order_url"]
    if "price_currency" in updates:
        obj.price_currency = updates["price_currency"]
    if "verified" in updates and updates["verified"] is not None:
        obj.is_verified = bool(updates["verified"])
    if "additional" in updates:
        obj.additional = updates["additional"]
    if "total_places" in updates:
        obj.total_places = updates["total_places"]

    if obj.total_places is not None:
        booked = _booked_places_for_event(db, obj.id)
        if booked > obj.total_places:
            raise HTTPException(
                status_code=400,
                detail="total_places cannot be less than already booked tickets",
            )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_out(obj, can_edit=True, booked_places=_booked_places_for_event(db, obj.id))


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    roles = _roles_map_for_user(db, user, [obj.id])
    if not _can_edit_event(obj, user, roles):
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(obj)
    db.commit()
    return None


@router.get("/events/all", response_model=UnifiedEventsOut)
async def unified_events(
    search: Optional[str] = Query(None, description="Search in multiple event fields"),
    city: Optional[str] = Query(None, description="Filter by city"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    min_price: Optional[int] = Query(None, description="Filter by minimum price"),
    max_price: Optional[int] = Query(None, description="Filter by maximum price"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
    request: Request = None,
) -> UnifiedEventsOut:
    effective_start_date = start_date or datetime.utcnow()

    current_user = _get_optional_current_user(db, request) if request else None
    favorite_event_ids: set[int] = set()
    if current_user:
        favorite_event_ids = {
            r[0]
            for r in db.query(UserFavoriteEvent.event_id)
            .filter(UserFavoriteEvent.user_id == current_user.id)
            .all()
        }

    if city:
        async def stream_city_events():
            all_items_by_uid: dict[str, UnifiedEventOut] = {}

            def include_or_update(unified: UnifiedEventOut) -> None:
                all_items_by_uid[unified.uid] = unified

            def current_page_snapshot() -> tuple[list[UnifiedEventOut], int]:
                ordered = sorted(
                    all_items_by_uid.values(),
                    key=_unified_start_date_sort_key,
                )
                total = len(ordered)
                return ordered[skip : skip + limit], total

            internal_query = db.query(Event).filter(Event.source_type == "INTERNAL")
            internal_query = _apply_search_filter(internal_query, search)
            internal_query = internal_query.filter(Event.city.ilike(f"%{city}%"))
            stream_start_date = effective_start_date
            if stream_start_date:
                internal_query = internal_query.filter(Event.startDate >= stream_start_date)
            if end_date:
                internal_query = internal_query.filter(Event.startDate <= end_date)
            if event_type:
                internal_query = internal_query.filter(Event.event_type.ilike(f"%{event_type}%"))

            internal_rows = internal_query.order_by(
                Event.startDate.asc().nullslast(),
                Event.created_at.desc(),
            ).all()
            internal_roles = _roles_map_for_user(db, current_user, [e.id for e in internal_rows])
            for e in internal_rows:
                if not _event_matches_filters(
                    e,
                    search=search,
                    city=city,
                    start_date=stream_start_date,
                    end_date=end_date,
                    min_price=min_price,
                    max_price=max_price,
                    event_type=event_type,
                ):
                    continue
                base = _to_out(
                    e,
                    is_saved=e.id in favorite_event_ids,
                    can_edit=_can_edit_event(e, current_user, internal_roles),
                )
                include_or_update(
                    UnifiedEventOut(
                        **base.model_dump(exclude={"uid"}),
                        kind=EventKind.internal,
                        uid=base.uid or f"internal:{e.id}",
                    )
                )

            # Include existing external events from DB so city results are not limited
            # only to newly scraped deltas.
            external_query = db.query(Event).filter(Event.source_type == "EXTERNAL")
            external_query = _apply_search_filter(external_query, search)
            external_query = external_query.filter(Event.city.ilike(f"%{city}%"))
            if stream_start_date:
                external_query = external_query.filter(Event.startDate >= stream_start_date)
            if end_date:
                external_query = external_query.filter(Event.startDate <= end_date)
            if event_type:
                external_query = external_query.filter(Event.event_type.ilike(f"%{event_type}%"))

            external_rows = external_query.order_by(
                Event.startDate.asc().nullslast(),
                Event.created_at.desc(),
            ).all()
            for e in external_rows:
                if not _event_matches_filters(
                    e,
                    search=search,
                    city=city,
                    start_date=stream_start_date,
                    end_date=end_date,
                    min_price=min_price,
                    max_price=max_price,
                    event_type=event_type,
                ):
                    continue
                base = _to_out(
                    e,
                    is_saved=e.id in favorite_event_ids,
                    can_edit=False,
                )
                include_or_update(
                    UnifiedEventOut(
                        **base.model_dump(exclude={"uid"}),
                        kind=EventKind.external,
                        uid=base.uid or f"external:{e.id}",
                    )
                )

            page_items, total_matching = current_page_snapshot()
            yield json.dumps(
                {
                    "items": [item.model_dump() for item in page_items],
                    "total": total_matching,
                    "done": False,
                }
            ) + "\n"

            if _city_scrape_recently_updated(db, city):
                page_items, total_matching = current_page_snapshot()
                yield json.dumps(
                    {
                        "items": [item.model_dump() for item in page_items],
                        "total": total_matching,
                        "done": True,
                    }
                ) + "\n"
                return

            try:
                city_for_scrape = city
                _ensure_city_name_en_column(db)
                city_row = db.query(City).filter(City.name == city).first()
                if city_row and city_row.name_en and city_row.name_en.strip():
                    city_for_scrape = city_row.name_en.strip()

                scraped_items = await _fetch_scraped_items(
                    ScrapeRequest(cities=[city_for_scrape], include_details=True)
                )
                new_events, updated_events = _upsert_scraped_items(db, scraped_items)
                _mark_city_scraped_now(db, city)
            except HTTPException as exc:
                yield json.dumps({"error": str(exc.detail), "done": True}) + "\n"
                return

            chunk_size = 20
            batch: list[UnifiedEventOut] = []
            for e in new_events + updated_events:
                if not _event_matches_filters(
                    e,
                    search=search,
                    city=city,
                    start_date=effective_start_date,
                    end_date=end_date,
                    min_price=min_price,
                    max_price=max_price,
                    event_type=event_type,
                ):
                    continue
                base = _to_out(
                    e,
                    is_saved=e.id in favorite_event_ids,
                    can_edit=False,
                )
                unified = UnifiedEventOut(
                    **base.model_dump(exclude={"uid"}),
                    kind=EventKind.external,
                    uid=base.uid or f"external:{e.id}",
                )
                include_or_update(unified)
                batch.append(unified)
                if len(batch) >= chunk_size:
                    page_items, total_matching = current_page_snapshot()
                    yield json.dumps(
                        {
                            "items": [item.model_dump() for item in page_items],
                            "total": total_matching,
                            "chunk": [item.model_dump() for item in batch],
                            "done": False,
                        }
                    ) + "\n"
                    batch = []

            if batch:
                page_items, total_matching = current_page_snapshot()
                yield json.dumps(
                    {
                        "items": [item.model_dump() for item in page_items],
                        "total": total_matching,
                        "chunk": [item.model_dump() for item in batch],
                        "done": False,
                    }
                ) + "\n"

            page_items, total_matching = current_page_snapshot()
            yield json.dumps(
                {
                    "items": [item.model_dump() for item in page_items],
                    "total": total_matching,
                    "done": True,
                }
            ) + "\n"

        return StreamingResponse(stream_city_events(), media_type="application/x-ndjson")

    query = db.query(Event)
    query = _apply_search_filter(query, search)

    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
        
    query = query.filter(Event.startDate >= effective_start_date)
        
    if end_date:
        query = query.filter(Event.startDate <= end_date)
        
    if event_type:
        query = query.filter(Event.event_type.ilike(f"%{event_type}%"))
        
    rows = query.order_by(
        Event.startDate.asc().nullslast(),
        Event.created_at.desc(),
    ).all()
    roles = _roles_map_for_user(db, current_user, [e.id for e in rows])
    
    items: list[UnifiedEventOut] = []
    for e in rows:
        # In-memory price filtering to avoid PostgreSQL cast errors on dirty string data
        if min_price is not None or max_price is not None:
            try:
                price = int(e.price_low) if e.price_low else None
            except (ValueError, TypeError):
                price = None
                
            if price is None:
                continue
                
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue

        base = _to_out(
            e,
            is_saved=e.id in favorite_event_ids,
            can_edit=_can_edit_event(e, current_user, roles),
        )
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal if e.source_type == "INTERNAL" else EventKind.external,
                uid=base.uid or (f"internal:{e.id}" if e.source_type == "INTERNAL" else f"external:{e.id}"),
            )
        )
        
    items = sorted(items, key=_unified_start_date_sort_key)
    total_count = len(items)
    paginated_items = items[skip : skip + limit]
    
    return UnifiedEventsOut(items=paginated_items, total=total_count)


@router.get("/events/lookup/{uid}", response_model=UnifiedEventOut)
def lookup_event(uid: str, db: Session = Depends(get_db), request: Request = None) -> UnifiedEventOut:
    obj = _find_event_by_uid(db, uid)
    if obj:
        current_user = _get_optional_current_user(db, request) if request else None
        is_saved = _is_event_saved_for_user(db, current_user, obj.id)
        roles = _roles_map_for_user(db, current_user, [obj.id])
        booked_places = _booked_places_for_event(db, obj.id) if obj.source_type == "INTERNAL" else None
        base = _to_out(
            obj,
            is_saved=is_saved,
            can_edit=_can_edit_event(obj, current_user, roles),
            booked_places=booked_places,
        )
        return UnifiedEventOut(
            **base.model_dump(exclude={"uid"}),
            kind=EventKind.internal if obj.source_type == "INTERNAL" else EventKind.external,
            uid=base.uid or (f"internal:{obj.id}" if obj.source_type == "INTERNAL" else f"external:{obj.id}"),
        )
    raise HTTPException(status_code=404, detail="Event not found")


@router.get("/events/me/favorites", response_model=UnifiedEventsOut)
def list_my_favorites(
    search: Optional[str] = Query(None, description="Search in multiple event fields"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnifiedEventsOut:
    fav_query = (
        db.query(Event)
        .join(UserFavoriteEvent, UserFavoriteEvent.event_id == Event.id)
        .filter(UserFavoriteEvent.user_id == user.id)
    )
    fav_query = _apply_search_filter(fav_query, search)
    total = fav_query.count()
    rows = (
        fav_query
        .order_by(UserFavoriteEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    roles = _roles_map_for_user(db, user, [e.id for e in rows])
    items: list[UnifiedEventOut] = []
    for e in rows:
        base = _to_out(e, is_saved=True, can_edit=_can_edit_event(e, user, roles))
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal if e.source_type == "INTERNAL" else EventKind.external,
                uid=base.uid or (f"internal:{e.id}" if e.source_type == "INTERNAL" else f"external:{e.id}"),
            )
        )
    return UnifiedEventsOut(items=items, total=total)


@router.get("/events/me/assigned", response_model=UnifiedEventsOut)
def list_my_assigned_events(
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnifiedEventsOut:
    subq = db.query(EventUser.event_id).filter(EventUser.user_id == user.id).subquery()
    query = (
        db.query(Event)
        .filter(
            Event.source_type == "INTERNAL",
            or_(Event.created_by_user_id == user.id, Event.id.in_(subq)),
        )
        .order_by(Event.created_at.desc())
    )
    total = query.count()
    rows = query.offset(skip).limit(limit).all()

    event_ids = [e.id for e in rows]
    roles = _roles_map_for_user(db, user, event_ids)

    items: list[UnifiedEventOut] = []
    for e in rows:
        base = _to_out(e, is_saved=False, can_edit=_can_edit_event(e, user, roles))
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal,
                uid=base.uid or f"internal:{e.id}",
            )
        )
    return UnifiedEventsOut(items=items, total=total)


@router.post("/events/{uid}/members", response_model=EventMembersUpsertResponse)
def upsert_event_members(
    uid: str,
    req: EventMembersUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EventMembersUpsertResponse:
    event = _find_event_by_uid(db, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.source_type != "INTERNAL":
        raise HTTPException(status_code=400, detail="Only internal events are supported")

    roles = _roles_map_for_user(db, user, [event.id])
    if not _can_edit_event(event, user, roles):
        raise HTTPException(status_code=403, detail="Not allowed")

    added: list[str] = []
    updated: list[str] = []
    missing: list[str] = []

    for email in req.emails:
        target = db.query(User).filter(User.email == str(email)).first()
        if not target:
            missing.append(str(email))
            continue

        existing = (
            db.query(EventUser)
            .filter(EventUser.event_id == event.id, EventUser.user_id == target.id)
            .first()
        )
        if existing:
            desired = EventUserRole(req.role.value)
            if existing.role != desired:
                existing.role = desired
                db.add(existing)
                updated.append(target.email)
        else:
            db.add(EventUser(event_id=event.id, user_id=target.id, role=EventUserRole(req.role.value)))
            added.append(target.email)

    db.commit()
    return EventMembersUpsertResponse(role=req.role, added=added, updated=updated, missing=missing)


@router.get("/events/{uid}/members", response_model=List[EventMemberOut])
def list_event_members(
    uid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[EventMemberOut]:
    event = _find_event_by_uid(db, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.source_type != "INTERNAL":
        raise HTTPException(status_code=400, detail="Only internal events are supported")

    roles = _roles_map_for_user(db, user, [event.id])
    if not _has_event_access(event, user, roles):
        raise HTTPException(status_code=403, detail="Not allowed")

    rows = (
        db.query(EventUser, User)
        .join(User, User.id == EventUser.user_id)
        .filter(EventUser.event_id == event.id)
        .order_by(EventUser.created_at.asc())
        .all()
    )
    return [
        EventMemberOut(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=eu.role,
        )
        for eu, u in rows
    ]


@router.delete("/events/{uid}/members/{member_user_id}", status_code=204)
def delete_event_member(
    uid: str,
    member_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    event = _find_event_by_uid(db, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.source_type != "INTERNAL":
        raise HTTPException(status_code=400, detail="Only internal events are supported")

    roles = _roles_map_for_user(db, user, [event.id])
    if not _can_edit_event(event, user, roles):
        raise HTTPException(status_code=403, detail="Not allowed")

    if member_user_id == event.created_by_user_id:
        raise HTTPException(status_code=400, detail="Creator access cannot be removed")

    rel = (
        db.query(EventUser)
        .filter(EventUser.event_id == event.id, EventUser.user_id == member_user_id)
        .first()
    )
    if not rel:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(rel)
    db.commit()
    return None


@router.post("/events/me/favorites/{uid}", response_model=UnifiedEventOut, status_code=201)
def add_my_favorite(
    uid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnifiedEventOut:
    event = _find_event_by_uid(db, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = (
        db.query(UserFavoriteEvent)
        .filter(
            UserFavoriteEvent.user_id == user.id,
            UserFavoriteEvent.event_id == event.id,
        )
        .first()
    )
    if not existing:
        db.add(UserFavoriteEvent(user_id=user.id, event_id=event.id))
        db.commit()
    roles = _roles_map_for_user(db, user, [event.id])
    base = _to_out(event, is_saved=True, can_edit=_can_edit_event(event, user, roles))
    return UnifiedEventOut(
        **base.model_dump(exclude={"uid"}),
        kind=EventKind.internal if event.source_type == "INTERNAL" else EventKind.external,
        uid=base.uid or (f"internal:{event.id}" if event.source_type == "INTERNAL" else f"external:{event.id}"),
    )


@router.delete("/events/me/favorites/{uid}", status_code=204)
def remove_my_favorite(
    uid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    event = _find_event_by_uid(db, uid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.query(UserFavoriteEvent).filter(
        UserFavoriteEvent.user_id == user.id,
        UserFavoriteEvent.event_id == event.id,
    ).delete()
    db.commit()
    return None


@router.post("/events/scrape", response_model=UnifiedEventsOut, status_code=200)
async def scrape_events(req: ScrapeRequest, db: Session = Depends(get_db)):
    scraped_items = await _fetch_scraped_items(req)
    new_events, updated_events = _upsert_scraped_items(db, scraped_items)

    out_items = []
    for e in new_events + updated_events:
        base = _to_out(e)
        out_items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.external,
                uid=base.uid or f"external:{e.id}",
            )
        )
        
    return UnifiedEventsOut(items=out_items)
