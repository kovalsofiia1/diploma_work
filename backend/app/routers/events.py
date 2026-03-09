from typing import List, Optional
from datetime import datetime
import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate, EventOut, ExternalEventCreate, UnifiedEventsOut, UnifiedEventOut, EventKind, ScrapeRequest
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _to_out(e: Event) -> EventOut:
    return EventOut(
        id=e.id,
        uid=e.uid,
        name=e.name,
        type=None,
        url=e.source_url,
        order_url=None,
        startDate=e.startDate.isoformat() if isinstance(e.startDate, datetime) and e.startDate else None,
        endDate=e.endDate.isoformat() if isinstance(e.endDate, datetime) and e.endDate else None,
        location_name=e.location_name,
        city=e.city,
        price_low=None,
        price_high=None,
        price_currency=None,
        image=None,
        source=e.source_name or "platform",
        verified=e.is_verified,
    )


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EventOut:
    obj = Event(
        name=data.name,
        startDate=_parse_dt(data.startDate),
        endDate=_parse_dt(data.endDate),
        location_name=data.location_name,
        city=data.city,
        # unified fields
        source_type="INTERNAL",
        source_name=data.source or "platform",
        source_event_id=None,
        source_url=data.url,
        is_verified=True if data.verified is None else data.verified,
        created_by_user_id=user.id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    if not obj.uid:
        obj.uid = f"internal:{obj.id}"
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return _to_out(obj)


@router.get("/events", response_model=List[EventOut])
def list_events(db: Session = Depends(get_db)) -> List[EventOut]:
    rows = db.query(Event).filter(Event.source_type == "INTERNAL").order_by(Event.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/events/{event_id:int}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_out(obj)


@router.put("/events/{event_id:int}", response_model=EventOut)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EventOut:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
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
    if "verified" in updates and updates["verified"] is not None:
        obj.is_verified = bool(updates["verified"])
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_out(obj)


@router.delete("/events/{event_id:int}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "INTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(obj)
    db.commit()
    return None


@router.post("/external-events", response_model=EventOut, status_code=201)
def add_external_event(data: ExternalEventCreate, db: Session = Depends(get_db)) -> EventOut:
    obj = Event(
        name=data.name,
        startDate=_parse_dt(data.startDate),
        endDate=_parse_dt(data.endDate),
        location_name=data.location_name,
        city=data.city,
        source_type="EXTERNAL",
        source_name=data.source or "karabas.com",
        source_event_id=None,
        source_url=data.url,
        is_verified=True if data.verified is None else data.verified,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    if not obj.uid:
        obj.uid = f"external:{obj.id}"
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return _to_out(obj)


@router.get("/external-events", response_model=List[EventOut])
def list_external_events(db: Session = Depends(get_db)) -> List[EventOut]:
    rows = db.query(Event).filter(Event.source_type == "EXTERNAL").order_by(Event.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/external-events/{event_id:int}", response_model=EventOut)
def get_external_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    obj = db.query(Event).filter(Event.id == event_id, Event.source_type == "EXTERNAL").first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_out(obj)


@router.get("/events/all", response_model=UnifiedEventsOut)
def unified_events(db: Session = Depends(get_db)) -> UnifiedEventsOut:
    rows = db.query(Event).order_by(Event.created_at.desc()).all()
    items: list[UnifiedEventOut] = []
    for e in rows:
        base = _to_out(e)
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal if e.source_type == "INTERNAL" else EventKind.external,
                uid=base.uid or (f"internal:{e.id}" if e.source_type == "INTERNAL" else f"external:{e.id}"),
            )
        )
    # Optional: sort by startDate or created time; keep simple for now
    return UnifiedEventsOut(items=items)


@router.get("/events/lookup/{uid}", response_model=UnifiedEventOut)
def lookup_event(uid: str, db: Session = Depends(get_db)) -> UnifiedEventOut:
    obj = db.query(Event).filter(Event.uid == uid).first()
    if obj:
        base = _to_out(obj)
        return UnifiedEventOut(
            **base.model_dump(exclude={"uid"}),
            kind=EventKind.internal if obj.source_type == "INTERNAL" else EventKind.external,
            uid=base.uid or (f"internal:{obj.id}" if obj.source_type == "INTERNAL" else f"external:{obj.id}"),
        )
    # Fallback: parse uid as "{kind}:{id}" and try numeric id lookup (for legacy rows without uid)
    if ":" in uid:
        kind, raw_id = uid.split(":", 1)
        if raw_id.isdigit():
            num_id = int(raw_id)
            obj = db.query(Event).filter(Event.id == num_id).first()
            if obj:
                base = _to_out(obj)
                return UnifiedEventOut(
                    **base.model_dump(exclude={"uid"}),
                    kind=EventKind.internal if obj.source_type == "INTERNAL" else EventKind.external,
                    uid=base.uid or (f"internal:{obj.id}" if obj.source_type == "INTERNAL" else f"external:{obj.id}"),
                )
    raise HTTPException(status_code=404, detail="Event not found")


@router.post("/events/scrape", status_code=200)
async def scrape_events(req: ScrapeRequest):
    """
    Calls the parser-service to fetch events for the given cities.
    Currently just returns the parsed events. Later, we will save them to the DB.
    """
    PARSER_SERVICE_URL = "http://localhost:8010/scrape/events"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                PARSER_SERVICE_URL,
                json=req.model_dump(),
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error communicating with parser-service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Parser service returned an error: {e.response.text}")


@router.post("/events/import-sample", response_model=UnifiedEventsOut, status_code=201)
def import_sample_external(db: Session = Depends(get_db)) -> UnifiedEventsOut:
    # Hardcoded sample "scrapingservice" payloads
    samples = [
        {
            "source_name": "concert.ua",
            "source_event_id": "12345",
            "title": "Imagine Dragons",
            "city": "Kyiv",
            "startDate": "2026-04-04T17:00:00Z",
            "url": "https://concert.ua/ua/event/imaginedragons",
        },
        {
            "source_name": "ticketmaster",
            "source_event_id": "abc-777",
            "title": "The Weeknd",
            "city": "Lviv",
            "startDate": "2026-05-12T20:00:00Z",
            "url": "https://ticketmaster.example/show/the-weeknd",
        },
    ]
    imported: list[Event] = []
    for s in samples:
        existing = (
            db.query(Event)
            .filter(Event.source_name == s["source_name"], Event.source_event_id == s["source_event_id"])
            .first()
        )
        if existing:
            continue
        obj = Event(
            name=s["title"],
            startDate=_parse_dt(s.get("startDate")),
            endDate=None,
            location_name=None,
            city=s.get("city"),
            source_type="EXTERNAL",
            source_name=s["source_name"],
            source_event_id=s["source_event_id"],
            source_url=s["url"],
            is_verified=True,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        if not obj.uid:
            obj.uid = f"external:{obj.id}"
            db.add(obj)
            db.commit()
            db.refresh(obj)
        imported.append(obj)
    items = []
    for e in imported:
        base = _to_out(e)
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.external if e.source_type == "EXTERNAL" else EventKind.internal,
                uid=base.uid or (f"external:{e.id}" if e.source_type == "EXTERNAL" else f"internal:{e.id}"),
            )
        )
    return UnifiedEventsOut(items=items)

