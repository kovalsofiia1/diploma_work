from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import typing
from fastapi.responses import StreamingResponse, JSONResponse
import json

class UnicodeJSONResponse(JSONResponse):
    def render(self, content: typing.Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

from app.models import ScrapeEventsRequest, ScrapeEventsResponse
from app.scraper import Scraper, build_batches
from app.parsers.dou_adapter import DouParser


def _repo_root() -> str:
    # .../diploma/parser-service/app/main.py -> repo root is 2 levels up from `parser-service`
    return str(Path(__file__).resolve().parents[2])


app = FastAPI(title="Parser Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper = Scraper(repo_root=_repo_root())


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/scrape/events", response_class=UnicodeJSONResponse, response_model=ScrapeEventsResponse, tags=["scrape"])
async def scrape_events(req: ScrapeEventsRequest) -> ScrapeEventsResponse:
    items, meta = await scraper.scrape_all(req)
    batches = build_batches(items, batch_size=req.batch_size)
    return ScrapeEventsResponse(items=items, batches=batches, meta=meta)


@app.post("/scrape/events/stream", tags=["scrape"])
async def scrape_events_stream(req: ScrapeEventsRequest):
    req.include_details = True
    return StreamingResponse(
        scraper.stream_batches(req),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )

@app.post("/scrape/dou", response_class=UnicodeJSONResponse, response_model=ScrapeEventsResponse, tags=["scrape"])
async def scrape_dou_events(concurrency: int = 5, max_pages: int = None) -> ScrapeEventsResponse:
    dou_parser = DouParser(city_index=scraper.city_index)
    items = await dou_parser.scrape_all_events(max_pages=max_pages, concurrency=concurrency)
    
    meta = {
        "source": "dou.ua",
        "total_items": len(items),
        "concurrency": concurrency,
        "max_pages": max_pages
    }
    
    batches = build_batches(items, batch_size=50)
    return ScrapeEventsResponse(items=items, batches=batches, meta=meta)


