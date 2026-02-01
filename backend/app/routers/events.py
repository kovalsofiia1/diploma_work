from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import InternalEvent, ExternalEvent
from app.schemas.event import EventCreate, EventUpdate, EventOut, ExternalEventCreate, UnifiedEventsOut, UnifiedEventOut, EventKind
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter()


def _to_out(e: InternalEvent | ExternalEvent) -> EventOut:
    return EventOut(
        id=e.id,
        uid=getattr(e, "uid", None),
        name=e.name,
        type=e.type,
        url=e.url,
        order_url=e.order_url,
        startDate=e.startDate,
        endDate=e.endDate,
        location_name=e.location_name,
        city=e.city,
        price_low=e.price_low,
        price_high=e.price_high,
        price_currency=e.price_currency,
        image=e.image,
        source=e.source,
        verified=e.verified,
    )


@router.post("/events", response_model=EventOut, status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EventOut:
    obj = InternalEvent(
        name=data.name,
        type=data.type,
        url=data.url,
        order_url=data.order_url,
        startDate=data.startDate,
        endDate=data.endDate,
        location_name=data.location_name,
        city=data.city,
        price_low=data.price_low,
        price_high=data.price_high,
        price_currency=data.price_currency,
        image=data.image,
        source=data.source or "internal",
        verified=True if data.verified is None else data.verified,
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
    rows = db.query(InternalEvent).order_by(InternalEvent.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/events/{event_id:int}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    obj = db.query(InternalEvent).filter(InternalEvent.id == event_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_out(obj)


@router.put("/events/{event_id:int}", response_model=EventOut)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> EventOut:
    obj = db.query(InternalEvent).filter(InternalEvent.id == event_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_out(obj)


@router.delete("/events/{event_id:int}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    obj = db.query(InternalEvent).filter(InternalEvent.id == event_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    db.delete(obj)
    db.commit()
    return None


@router.post("/external-events", response_model=EventOut, status_code=201)
def add_external_event(data: ExternalEventCreate, db: Session = Depends(get_db)) -> EventOut:
    obj = ExternalEvent(
        name=data.name,
        type=data.type,
        url=data.url,
        order_url=data.order_url,
        startDate=data.startDate,
        endDate=data.endDate,
        location_name=data.location_name,
        city=data.city,
        price_low=data.price_low,
        price_high=data.price_high,
        price_currency=data.price_currency,
        image=data.image,
        source=data.source or "karabas.com",
        verified=True if data.verified is None else data.verified,
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
    rows = db.query(ExternalEvent).order_by(ExternalEvent.created_at.desc()).all()
    return [_to_out(r) for r in rows]


@router.get("/external-events/{event_id:int}", response_model=EventOut)
def get_external_event(event_id: int, db: Session = Depends(get_db)) -> EventOut:
    obj = db.query(ExternalEvent).filter(ExternalEvent.id == event_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Event not found")
    return _to_out(obj)


@router.get("/events/all", response_model=UnifiedEventsOut)
def unified_events(db: Session = Depends(get_db)) -> UnifiedEventsOut:
    internal = db.query(InternalEvent).all()
    external = db.query(ExternalEvent).all()
    items: list[UnifiedEventOut] = []
    for e in internal:
        base = _to_out(e)
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.internal,
                uid=base.uid or f"internal:{e.id}",
            )
        )
    for e in external:
        base = _to_out(e)
        items.append(
            UnifiedEventOut(
                **base.model_dump(exclude={"uid"}),
                kind=EventKind.external,
                uid=base.uid or f"external:{e.id}",
            )
        )
    # Optional: sort by startDate or created time; keep simple for now
    return UnifiedEventsOut(items=items)


@router.get("/events/lookup/{uid}", response_model=UnifiedEventOut)
def lookup_event(uid: str, db: Session = Depends(get_db)) -> UnifiedEventOut:
    obj_i = db.query(InternalEvent).filter(InternalEvent.uid == uid).first()
    if obj_i:
        base = _to_out(obj_i)
        return UnifiedEventOut(
            **base.model_dump(exclude={"uid"}),
            kind=EventKind.internal,
            uid=base.uid or f"internal:{obj_i.id}",
        )
    obj_e = db.query(ExternalEvent).filter(ExternalEvent.uid == uid).first()
    if obj_e:
        base = _to_out(obj_e)
        return UnifiedEventOut(
            **base.model_dump(exclude={"uid"}),
            kind=EventKind.external,
            uid=base.uid or f"external:{obj_e.id}",
        )
    # Fallback: parse uid as "{kind}:{id}" and try numeric id lookup (for legacy rows without uid)
    if ":" in uid:
        kind, raw_id = uid.split(":", 1)
        if raw_id.isdigit():
            num_id = int(raw_id)
            if kind == "internal":
                obj_i = db.query(InternalEvent).filter(InternalEvent.id == num_id).first()
                if obj_i:
                    base = _to_out(obj_i)
                    return UnifiedEventOut(
                        **base.model_dump(exclude={"uid"}),
                        kind=EventKind.internal,
                        uid=base.uid or f"internal:{obj_i.id}",
                    )
            elif kind == "external":
                obj_e = db.query(ExternalEvent).filter(ExternalEvent.id == num_id).first()
                if obj_e:
                    base = _to_out(obj_e)
                    return UnifiedEventOut(
                        **base.model_dump(exclude={"uid"}),
                        kind=EventKind.external,
                        uid=base.uid or f"external:{obj_e.id}",
                    )
    raise HTTPException(status_code=404, detail="Event not found")

