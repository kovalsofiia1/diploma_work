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


def _cached_concert_items() -> list[dict[str, str | None]]:
    by_name: dict[str, str | None] = {}
    for city in scraper.city_index._concert_by_key.values():
        name = (city.name or "").strip()
        if not name:
            continue
        slug = (city.slug or "").strip() or None
        if name not in by_name or (slug and not by_name[name]):
            by_name[name] = slug
    return [{"name": name, "name_en": slug, "source": "concert.ua"} for name, slug in by_name.items()]


def _cached_karabas_items() -> list[dict[str, str | None]]:
    by_name: dict[str, str | None] = {}
    for city in scraper.city_index._karabas_by_key.values():
        name = (city.name or "").strip()
        if not name:
            continue
        subdomain = (city.subdomain or "").strip() or None
        if name not in by_name or (subdomain and not by_name[name]):
            by_name[name] = subdomain
    return [{"name": name, "name_en": subdomain, "source": "karabas.com"} for name, subdomain in by_name.items()]


def _concert_slug_from_href(href: str | None) -> str | None:
    if not href:
        return None
    m = re.search(r"/uk/([a-z0-9-]+)", href, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).lower()


def _karabas_subdomain_from_href(href: str | None) -> str | None:
    if not href:
        return None
    m = re.match(r"^https?://([a-z0-9-]+)\.karabas\.com/?", href, re.IGNORECASE)
    if not m:
        return None
    sub = m.group(1).lower()
    return None if sub in {"www", "karabas"} else sub


def _parse_concert_city_items(html: str) -> list[dict[str, str | None]]:
    ul_match = re.search(
        r'<ul\s+class="[^"]*\bcity-list\b[^"]*"\s+id="cityList"\s*>(?P<body>.*?)</ul>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body = ul_match.group("body") if ul_match else html
    out: list[dict[str, str | None]] = []
    seen_names: set[str] = set()

    for m in re.finditer(
        r'<li[^>]*class="[^"]*\bcity-list__item\b[^"]*"[^>]*>(?P<li_body>.*?)</li>',
        body,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        li_body = m.group("li_body") or ""
        a_match = re.search(
            r'<a[^>]*class="[^"]*\bcity-list__link\b[^"]*"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<a_body>.*?)</a>',
            li_body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not a_match:
            continue
        href = a_match.group("href")
        a_body = a_match.group("a_body") or ""
        name_match = re.search(r"<b>\s*([^<]+?)\s*</b>", a_body, flags=re.DOTALL | re.IGNORECASE)
        name = name_match.group(1).strip() if name_match else _clean_text(a_body)
        if not name:
            continue
        key = name.casefold()
        if key in seen_names:
            continue
        seen_names.add(key)
        out.append(
            {
                "name": name,
                "name_en": _concert_slug_from_href(href),
                "source": "concert.ua",
            }
        )
    return out


def _parse_karabas_city_items(html: str) -> list[dict[str, str | None]]:
    start_idx = html.find('class="modal-scrollable one-country_tab active"')
    if start_idx == -1:
        m = re.search(r'class="[^"]*\bone-country_tab\b[^"]*\bactive\b[^"]*"', html, re.IGNORECASE)
        start_idx = m.start() if m else 0
    next_idx = html.find('class="modal-scrollable one-country_tab', start_idx + 1)
    block = html[start_idx : (next_idx if next_idx != -1 else len(html))]

    out: list[dict[str, str | None]] = []
    seen_names: set[str] = set()
    for cls, href, inner in _ANCHOR_RE.findall(block):
        if "ignore" in (cls or "").lower():
            continue
        name_match = _NAME_SPAN_RE.search(inner)
        name = _clean_text(name_match.group(1)) if name_match else _clean_text(inner)
        if not name or name == "Усі міста":
            continue
        key = name.casefold()
        if key in seen_names:
            continue
        seen_names.add(key)
        out.append(
            {
                "name": name,
                "name_en": _karabas_subdomain_from_href(href),
                "source": "karabas.com",
            }
        )
    return out


@app.get("/cities", tags=["cities"])
async def list_parser_cities() -> dict:
    async with httpx.AsyncClient(follow_redirects=True, headers=_LIVE_CITY_HEADERS, timeout=25.0) as client:
        concert_task = client.get(_CONCERT_CITIES_URL)
        karabas_task = client.get(_KARABAS_CITIES_URL)
        concert_resp, karabas_resp = await asyncio.gather(concert_task, karabas_task, return_exceptions=True)

    errors: list[str] = []
    concert_items: list[dict[str, str | None]] = []
    karabas_items: list[dict[str, str | None]] = []

    if isinstance(concert_resp, Exception):
        errors.append(f"concert.ua live fetch failed: {concert_resp}")
        concert_items = _cached_concert_items()
    else:
        try:
            concert_resp.raise_for_status()
            concert_items = _parse_concert_city_items(concert_resp.text)
            if not concert_items:
                raise RuntimeError("no cities parsed")
        except Exception as exc:
            errors.append(f"concert.ua parse fallback: {exc}")
            concert_items = _cached_concert_items()

    if isinstance(karabas_resp, Exception):
        errors.append(f"karabas.com live fetch failed: {karabas_resp}")
        karabas_items = _cached_karabas_items()
    else:
        try:
            karabas_resp.raise_for_status()
            karabas_items = _parse_karabas_city_items(karabas_resp.text)
            if not karabas_items:
                raise RuntimeError("no cities parsed")
        except Exception as exc:
            errors.append(f"karabas.com parse fallback: {exc}")
            karabas_items = _cached_karabas_items()

    city_items = concert_items + karabas_items
    names = sorted({(item.get("name") or "").strip() for item in city_items if (item.get("name") or "").strip()})
    return {
        "cities": names,
        "city_items": city_items,
        "meta": {
            "concert_count": len(concert_items),
            "karabas_count": len(karabas_items),
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


