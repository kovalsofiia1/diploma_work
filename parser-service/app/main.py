from __future__ import annotations

from pathlib import Path
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import typing
from fastapi.responses import StreamingResponse, JSONResponse
import json
import re
import httpx

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


_CONCERT_CITIES_URL = "https://concert.ua/uk/kyiv"
_KARABAS_CITIES_URL = "https://lviv.karabas.com/"
_LIVE_CITY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
_WS_RE = re.compile(r"\s+")
_TAGS_RE = re.compile(r"<[^>]+>")
_ANCHOR_RE = re.compile(
    r'<a[^>]+class="([^"]*\bfiltered\b[^"]*)"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_NAME_SPAN_RE = re.compile(
    r'<span[^>]*class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)


def _clean_text(fragment: str) -> str:
    text = _TAGS_RE.sub("", fragment or "")
    return _WS_RE.sub(" ", text).strip()


def _cached_concert_names() -> set[str]:
    return {city.name.strip() for city in scraper.city_index._concert_by_key.values() if city.name and city.name.strip()}


def _cached_karabas_names() -> set[str]:
    return {city.name.strip() for city in scraper.city_index._karabas_by_key.values() if city.name and city.name.strip()}


def _parse_concert_city_names(html: str) -> set[str]:
    ul_match = re.search(
        r'<ul\s+class="[^"]*\bcity-list\b[^"]*"\s+id="cityList"\s*>(?P<body>.*?)</ul>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body = ul_match.group("body") if ul_match else html
    names: set[str] = set()

    for m in re.finditer(
        r'<li[^>]*class="[^"]*\bcity-list__item\b[^"]*"[^>]*>(?P<li_body>.*?)</li>',
        body,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        li_body = m.group("li_body") or ""
        a_match = re.search(
            r'<a[^>]*class="[^"]*\bcity-list__link\b[^"]*"[^>]*>(?P<a_body>.*?)</a>',
            li_body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not a_match:
            continue
        a_body = a_match.group("a_body") or ""
        name_match = re.search(r"<b>\s*([^<]+?)\s*</b>", a_body, flags=re.DOTALL | re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else _clean_text(a_body)
        if name:
            names.add(name)
    return names


def _parse_karabas_city_names(html: str) -> set[str]:
    start_idx = html.find('class="modal-scrollable one-country_tab active"')
    if start_idx == -1:
        m = re.search(r'class="[^"]*\bone-country_tab\b[^"]*\bactive\b[^"]*"', html, re.IGNORECASE)
        start_idx = m.start() if m else 0
    next_idx = html.find('class="modal-scrollable one-country_tab', start_idx + 1)
    block = html[start_idx : (next_idx if next_idx != -1 else len(html))]

    names: set[str] = set()
    for cls, _href, inner in _ANCHOR_RE.findall(block):
        if "ignore" in (cls or "").lower():
            continue
        name_match = _NAME_SPAN_RE.search(inner)
        name = _clean_text(name_match.group(1)) if name_match else _clean_text(inner)
        if name and name != "Усі міста":
            names.add(name)
    return names


@app.get("/cities", tags=["cities"])
async def list_parser_cities() -> dict:
    async with httpx.AsyncClient(follow_redirects=True, headers=_LIVE_CITY_HEADERS, timeout=25.0) as client:
        concert_task = client.get(_CONCERT_CITIES_URL)
        karabas_task = client.get(_KARABAS_CITIES_URL)
        concert_resp, karabas_resp = await asyncio.gather(concert_task, karabas_task, return_exceptions=True)

    errors: list[str] = []
    concert_names: set[str] = set()
    karabas_names: set[str] = set()

    if isinstance(concert_resp, Exception):
        errors.append(f"concert.ua live fetch failed: {concert_resp}")
        concert_names = _cached_concert_names()
    else:
        try:
            concert_resp.raise_for_status()
            concert_names = _parse_concert_city_names(concert_resp.text)
            if not concert_names:
                raise RuntimeError("no cities parsed")
        except Exception as exc:
            errors.append(f"concert.ua parse fallback: {exc}")
            concert_names = _cached_concert_names()

    if isinstance(karabas_resp, Exception):
        errors.append(f"karabas.com live fetch failed: {karabas_resp}")
        karabas_names = _cached_karabas_names()
    else:
        try:
            karabas_resp.raise_for_status()
            karabas_names = _parse_karabas_city_names(karabas_resp.text)
            if not karabas_names:
                raise RuntimeError("no cities parsed")
        except Exception as exc:
            errors.append(f"karabas.com parse fallback: {exc}")
            karabas_names = _cached_karabas_names()

    names = set()
    names.update(concert_names)
    names.update(karabas_names)
    return {
        "cities": sorted(names),
        "meta": {
            "concert_count": len(concert_names),
            "karabas_count": len(karabas_names),
            "errors": errors,
        },
    }


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


