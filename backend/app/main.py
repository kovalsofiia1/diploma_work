import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.routers import auth
from app.routers import events
from app.routers import tickets
from app.routers import booking
from app.routers import checkin
from app.routers import cron
from app.db.session import create_all_tables
from app.core.config import get_settings
from app.services.scheduler_service import (
    cleanup_city_activity_log_job,
    cleanup_past_external_events_job,
    scrape_popular_cities_job,
    scrape_then_send_city_events_digest_job,
    sync_cities_job,
)

logger = logging.getLogger(__name__)


async def run_startup_jobs() -> None:
    try:
        await sync_cities_job()
        await scrape_popular_cities_job()
        cleanup_past_external_events_job()
    except Exception:
        logger.exception("Startup background jobs failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For initial dev convenience; use Alembic migrations in real environments
    create_all_tables()
    settings = get_settings()

    # Run initial bootstrap without blocking the API from accepting requests.
    startup_task = asyncio.create_task(run_startup_jobs())

    # Periodic scheduler jobs
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scrape_popular_cities_job,
        trigger=IntervalTrigger(hours=max(1, settings.scrape_interval_hours)),
        id="scrape_popular_cities",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_past_external_events_job,
        trigger=IntervalTrigger(hours=max(1, settings.cleanup_interval_hours)),
        id="cleanup_past_external_events",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_city_activity_log_job,
        trigger=IntervalTrigger(hours=max(1, settings.cleanup_interval_hours)),
        id="cleanup_city_activity_log",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_cities_job,
        trigger=IntervalTrigger(hours=12),
        id="sync_cities",
        replace_existing=True,
    )
    scheduler.add_job(
        scrape_then_send_city_events_digest_job,
        trigger=CronTrigger(
            hour=max(0, min(23, settings.city_digest_hour_utc)),
            minute=max(0, min(59, settings.city_digest_minute_utc)),
        ),
        id="daily_city_digest_after_scrape",
        replace_existing=True,
    )
    scheduler.start()
    yield
    startup_task.cancel()
    scheduler.shutdown(wait=False)


app = FastAPI(title="Event Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(events.router, tags=["events"])
app.include_router(tickets.router, tags=["tickets"])
app.include_router(booking.router, tags=["booking"])
app.include_router(checkin.router, tags=["checkin"])
app.include_router(cron.router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}

