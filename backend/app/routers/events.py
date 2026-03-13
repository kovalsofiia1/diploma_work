from typing import List, Optional
from datetime import datetime
import httpx

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import cast, Integer

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
        description=data.description,
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
    obj = db.query(Event).filter(Event.id == event_id).first()
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
def unified_events(
    city: Optional[str] = Query(None, description="Filter by city"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (inclusive)"),
    min_price: Optional[int] = Query(None, description="Filter by minimum price"),
    max_price: Optional[int] = Query(None, description="Filter by maximum price"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db)
) -> UnifiedEventsOut:
    query = db.query(Event)
    
    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
        
    if start_date:
        query = query.filter(Event.startDate >= start_date)
        
    if end_date:
        query = query.filter(Event.startDate <= end_date)
        
    if event_type:
        query = query.filter(Event.event_type.ilike(f"%{event_type}%"))
        
    rows = query.order_by(Event.created_at.desc()).all()
    
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

        base = _to_out(e)
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal if e.source_type == "INTERNAL" else EventKind.external,
                uid=base.uid or (f"internal:{e.id}" if e.source_type == "INTERNAL" else f"external:{e.id}"),
            )
        )
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


# TODO: add scraping of detailed info for karabas and concert.ua
@router.post("/events/scrape", response_model=UnifiedEventsOut, status_code=200)
async def scrape_events(req: ScrapeRequest, db: Session = Depends(get_db)):
    """
    Calls the parser-service to fetch events for the given cities.
    Deduplicates the events, checks if they exist in the DB, and saves the new ones.
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
            data = response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error communicating with parser-service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Parser service returned an error: {e.response.text}")

    scraped_items = data.get("items", [])
    
    # 1. In-memory deduplication (remove duplicates from the scraped batch itself)
    unique_items = []
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
    urls_to_check = [item.get("url") for item in unique_items if item.get("url")]
    existing_events_by_url = {}
    
    if urls_to_check:
        existing_records = db.query(Event).filter(Event.source_url.in_(urls_to_check)).all()
        existing_events_by_url = {r.source_url: r for r in existing_records if r.source_url}

    new_events = []
    updated_events = []
    
    for item in unique_items:
        url = item.get("url")
        
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
        if url and url in existing_events_by_url:
            existing = existing_events_by_url[url]
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
            
        # If no URL, do a fallback query to check if it exists by name and date
        if not url:
            existing = db.query(Event).filter(
                Event.source_name == item.get("source"),
                Event.name == item.get("name"),
                Event.startDate == _parse_dt(item.get("startDate"))
            ).first()
            if existing:
                changed = False
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
            source_url=url[:1024] if url else None,
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

    # 5. Return the newly added/updated events
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
