from __future__ import annotations

from fastapi import APIRouter

from app.services.scheduler_service import schedule_city_scraping

router = APIRouter(prefix="/cron", tags=["cron"])


@router.post("/scrape-cities", status_code=200)
async def cron_scrape_cities() -> dict:
    return await schedule_city_scraping()
