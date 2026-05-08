from __future__ import annotations

from fastapi import APIRouter

from app.services.scheduler_service import (
    schedule_city_scraping,
    scrape_then_send_city_events_digest_job,
    send_new_city_events_digest_job,
)

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/scrape-cities", status_code=200)
async def cron_scrape_cities() -> dict:
    return await schedule_city_scraping()


@router.post("/send-city-digest", status_code=200)
async def cron_send_city_digest() -> dict:
    return send_new_city_events_digest_job()


@router.post("/scrape-and-send-city-digest", status_code=200)
async def cron_scrape_and_send_city_digest() -> dict:
    await scrape_then_send_city_events_digest_job()
    return {"status": "ok"}
