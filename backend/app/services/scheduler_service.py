from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, case, desc, func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.event import City, CityActivityLog, CityActivityType, CityScrapeState, Event
from app.schemas.event import ScrapeRequest
from app.routers import events as events_router

logger = logging.getLogger(__name__)

SCRAPE_COOLDOWN_HOURS = 12
MAX_CITIES_PER_RUN = 10
ACTIVITY_RETENTION_DAYS = 14
ACTIVITY_LOOKBACK_DAYS = 14
SCORE_SUBSCRIPTION = 10
SCORE_SEARCH = 5


def _popular_cities_from_settings() -> list[str]:
    settings = get_settings()
    raw = (settings.popular_cities or "").strip()
    if not raw:
        return []
    return [city.strip() for city in raw.split(",") if city.strip()]


def _normalize_city(city: str) -> str:
    return city.strip()


def log_city_activity(db: Session, city: str, activity_type: CityActivityType) -> None:
    normalized_city = _normalize_city(city)
    if not normalized_city:
        return
    db.add(CityActivityLog(city=normalized_city, activity_type=activity_type))
    db.commit()


def cleanup_city_activity_log(db: Session, *, retention_days: int = ACTIVITY_RETENTION_DAYS) -> int:
    cutoff = datetime.utcnow() - timedelta(days=max(1, retention_days))
    deleted = db.query(CityActivityLog).filter(CityActivityLog.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return int(deleted or 0)


def _city_parser_name(db: Session, city: str) -> str:
    city_name = _normalize_city(city)
    city_row = db.query(City).filter(City.name == city_name).first()
    if city_row and city_row.name_en and city_row.name_en.strip():
        return city_row.name_en.strip()
    return city_name


def _city_scores_from_activity(db: Session, *, lookback_days: int = ACTIVITY_LOOKBACK_DAYS) -> dict[str, int]:
    cutoff = datetime.utcnow() - timedelta(days=max(1, lookback_days))
    rows = (
        db.query(
            CityActivityLog.city,
            func.sum(
                case(
                    (CityActivityLog.activity_type == CityActivityType.subscription, SCORE_SUBSCRIPTION),
                    (CityActivityLog.activity_type == CityActivityType.search, SCORE_SEARCH),
                    else_=0,
                )
            ).label("score"),
        )
        .filter(CityActivityLog.created_at >= cutoff)
        .group_by(CityActivityLog.city)
        .order_by(desc("score"))
        .all()
    )
    return {str(city): int(score or 0) for city, score in rows if city}


def _claim_city_for_scraping(db: Session, city: str) -> bool:
    normalized_city = _normalize_city(city)
    if not normalized_city:
        return False

    now = datetime.utcnow()
    cooldown_since = now - timedelta(hours=SCRAPE_COOLDOWN_HOURS)

    state = (
        db.query(CityScrapeState)
        .filter(CityScrapeState.city_key == normalized_city)
        .first()
    )
    if state is None:
        try:
            db.add(
                CityScrapeState(
                    city_key=normalized_city,
                    city=normalized_city,
                    city_name=normalized_city,
                    is_scraping=False,
                    last_scraped_at=None,
                )
            )
            db.flush()
        except IntegrityError:
            db.rollback()

    claimed = (
        db.execute(
            update(CityScrapeState)
            .where(
                CityScrapeState.city_key == normalized_city,
                CityScrapeState.is_scraping.is_(False),
                or_(
                    CityScrapeState.last_scraped_at.is_(None),
                    CityScrapeState.last_scraped_at <= cooldown_since,
                ),
            )
            .values(is_scraping=True)
        ).rowcount
        or 0
    )
    db.commit()
    return bool(claimed)


def _finish_city_scraping(db: Session, city: str, *, success: bool) -> None:
    normalized_city = _normalize_city(city)
    if not normalized_city:
        return
    values: dict[str, Any] = {
        "is_scraping": False,
        "city": normalized_city,
        "city_name": normalized_city,
    }
    if success:
        values["last_scraped_at"] = datetime.utcnow()
    db.execute(
        update(CityScrapeState)
        .where(CityScrapeState.city_key == normalized_city)
        .values(**values)
    )
    db.commit()


async def _scrape_single_city(db: Session, city: str) -> tuple[int, int]:
    parser_city = _city_parser_name(db, city)
    logger.info("Scheduler: start scraping city=%s parser_city=%s", city, parser_city)
    req = ScrapeRequest(
        cities=[parser_city],
        sources=["karabas.com", "concert.ua", "dou.ua"],
        include_details=True,
        max_events_per_city=30,
    )
    scraped_items = await events_router._fetch_scraped_items(req)
    new_events, updated_events = events_router._upsert_scraped_items(db, scraped_items)
    return len(new_events), len(updated_events)


async def schedule_city_scraping() -> dict[str, Any]:
    settings = get_settings()
    max_cities = max(1, settings.scrape_max_cities_per_run or MAX_CITIES_PER_RUN)
    popular_cities = _popular_cities_from_settings()

    db = SessionLocal()
    total_new = 0
    total_updated = 0
    scraped_cities: list[str] = []
    activity_scores: dict[str, int] = {}
    try:
        activity_scores = _city_scores_from_activity(db)
        candidate_scores = dict(activity_scores)
        for city in popular_cities:
            if city not in candidate_scores:
                candidate_scores[city] = 1

        # Fallback for empty activity stream: scrape predefined popular cities.
        if not candidate_scores and popular_cities:
            candidate_scores = {city: 1 for city in popular_cities}

        # Join-like filter with city_scrape_state before selecting top cities.
        now = datetime.utcnow()
        cooldown_since = now - timedelta(hours=SCRAPE_COOLDOWN_HOURS)
        candidate_cities = list(candidate_scores.keys())
        existing_states = (
            db.query(CityScrapeState)
            .filter(CityScrapeState.city_key.in_(candidate_cities))
            .all()
            if candidate_cities
            else []
        )
        state_by_city = {row.city_key: row for row in existing_states}
        filtered_scores: dict[str, int] = {}
        for city, score in candidate_scores.items():
            state = state_by_city.get(city)
            if state and state.is_scraping:
                continue
            if state and state.last_scraped_at and state.last_scraped_at > cooldown_since:
                continue
            filtered_scores[city] = score

        sorted_candidates = sorted(
            filtered_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        logger.info(
            "Scheduler: scrape run started max_cities=%s activity_cities=%s candidate_cities=%s",
            max_cities,
            len(activity_scores),
            [city for city, _ in sorted_candidates[:max_cities]],
        )

        for city, score in sorted_candidates:
            if len(scraped_cities) >= max_cities:
                break

            claimed = _claim_city_for_scraping(db, city)
            if not claimed:
                logger.info("Scheduler: city skipped (locked or cooldown) city=%s score=%s", city, score)
                continue

            success = False
            try:
                new_count, updated_count = await _scrape_single_city(db, city)
                total_new += new_count
                total_updated += updated_count
                scraped_cities.append(city)
                success = True
                logger.info(
                    "Scheduler: city scraped city=%s score=%s new=%s updated=%s",
                    city,
                    score,
                    new_count,
                    updated_count,
                )
            except Exception as exc:
                logger.exception("Scheduler: city scrape failed city=%s error=%s", city, exc)
            finally:
                _finish_city_scraping(db, city, success=success)

        return {
            "selected_cities": scraped_cities,
            "selected_count": len(scraped_cities),
            "max_cities_per_run": max_cities,
            "activity_city_count": len(activity_scores),
            "total_new_events": total_new,
            "total_updated_events": total_updated,
            "scrape_interval_hours": settings.scrape_interval_hours,
        }
    except Exception as exc:
        logger.exception("Scheduler: schedule_city_scraping failed: %s", exc)
        return {
            "selected_cities": [],
            "selected_count": 0,
            "max_cities_per_run": max_cities,
            "activity_city_count": len(activity_scores),
            "total_new_events": 0,
            "total_updated_events": 0,
            "error": str(exc),
        }
    finally:
        db.close()


async def scrape_popular_cities_job() -> None:
    result = await schedule_city_scraping()
    logger.info("Scheduler: scrape job finished result=%s", result)


def cleanup_past_external_events_job() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        deleted = (
            db.query(Event)
            .filter(
                Event.source_type == "EXTERNAL",
                or_(
                    and_(Event.endDate.isnot(None), Event.endDate < now),
                    and_(Event.endDate.is_(None), Event.startDate < now),
                ),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("Scheduler: deleted %s past external events", int(deleted or 0))
    except Exception as exc:
        db.rollback()
        logger.exception("Scheduler: cleanup_past_external_events_job failed: %s", exc)
    finally:
        db.close()


def cleanup_city_activity_log_job() -> None:
    db = SessionLocal()
    try:
        settings = get_settings()
        retention_days = max(1, settings.city_activity_retention_days or ACTIVITY_RETENTION_DAYS)
        deleted = cleanup_city_activity_log(db, retention_days=retention_days)
        logger.info("Scheduler: deleted %s old city activity rows", deleted)
    except Exception as exc:
        db.rollback()
        logger.exception("Scheduler: cleanup_city_activity_log_job failed: %s", exc)
    finally:
        db.close()


async def sync_cities_job() -> None:
    """
    Periodic job: refresh local `cities` reference table from parser-service
    (live sources) plus cities of INTERNAL events. Mirrors logic of
    POST /cities/sync but runs without a user context.
    """
    db = SessionLocal()
    try:
        events_router._ensure_city_name_en_column(db)
        parser_city_items = await events_router._fetch_parser_cities()

        internal_city_rows = (
            db.query(Event.city)
            .filter(Event.source_type == "INTERNAL", Event.city.isnot(None))
            .all()
        )
        internal_cities = [
            str(row[0]).strip()
            for row in internal_city_rows
            if row and row[0] and str(row[0]).strip()
        ]

        city_map: dict[str, Any] = {}
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

        logger.info(
            "Scheduler: cities synced deleted=%s inserted=%s with_en=%s",
            old_count,
            len(city_map),
            len([v for v in city_map.values() if v]),
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Scheduler: sync_cities_job failed: %s", exc)
    finally:
        db.close()
