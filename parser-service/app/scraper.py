from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models import NormalizedEvent, ScrapeBatch, ScrapeEventsRequest
from app.parsers.cities_index import CityIndex
from app.parsers.concert_adapter import ConcertParser
from app.parsers.karabas_adapter import KarabasParser
from app.parsers.dou_adapter import DouParser


DEFAULT_HEADERS = {
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _chunk(items: list[NormalizedEvent], size: int) -> list[list[NormalizedEvent]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def build_batches(items: list[NormalizedEvent], batch_size: int) -> list[ScrapeBatch]:
    chunks = _chunk(items, batch_size)
    out: list[ScrapeBatch] = []
    for i, c in enumerate(chunks):
        out.append(ScrapeBatch(batch_index=i, items=c, done=False))
    if out:
        out[-1].done = True
    return out


def _guess_karabas_url(city_or_subdomain: str) -> Optional[str]:
    s = (city_or_subdomain or "").strip().casefold()
    if not s:
        return None
    if re.fullmatch(r"[a-z0-9-]{2,64}", s):
        return f"https://{s}.karabas.com/"
    return None


def _guess_concert_url(city_or_slug: str) -> Optional[str]:
    s = (city_or_slug or "").strip().casefold()
    if not s:
        return None
    if re.fullmatch(r"[a-z0-9-]{2,64}", s):
        return f"https://concert.ua/uk/{s}"
    return None


async def fetch_text(client: httpx.AsyncClient, url: str, timeout_seconds: float) -> str:
    r = await client.get(url, timeout=timeout_seconds, follow_redirects=True, headers=DEFAULT_HEADERS)
    r.raise_for_status()
    enc = r.encoding or "utf-8"
    return r.content.decode(enc, errors="replace")


async def _enrich_concert_details(
    client: httpx.AsyncClient,
    parser: ConcertParser,
    events: list[NormalizedEvent],
    timeout_seconds: float,
    max_concurrency: int,
) -> tuple[list[NormalizedEvent], list[dict[str, Any]]]:
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))
    errors: list[dict[str, Any]] = []

    async def one(ev: NormalizedEvent) -> NormalizedEvent:
        if not ev.url:
            return ev
        async with sem:
            try:
                html = await fetch_text(client, ev.url, timeout_seconds=timeout_seconds)
                details = parser.parse_detail(html)
            except Exception as exc:
                errors.append({"url": ev.url, "error": str(exc)})
                return ev

        # Map detail fields -> normalized
        start_iso = details.get("start_date_iso")
        end_iso = details.get("end_date_iso")
        loc_name = details.get("location_name")
        city = details.get("address_locality")
        desc = details.get("detail_description")
        offer_price = details.get("offer_price")
        offer_cur = details.get("offer_currency")
        offer_url = details.get("offer_url")

        merged = ev.model_copy(deep=True)
        if start_iso and not merged.startDate:
            merged.startDate = str(start_iso)
        if end_iso and not merged.endDate:
            merged.endDate = str(end_iso)
        if loc_name and not merged.location_name:
            merged.location_name = str(loc_name)
        if city and not merged.city:
            merged.city = str(city)
        if desc and not merged.description:
            merged.description = str(desc)
        if offer_cur and not merged.price_currency:
            merged.price_currency = str(offer_cur)
        if offer_url and not merged.order_url:
            merged.order_url = str(offer_url)
        if offer_price and not merged.price_low:
            merged.price_low = str(offer_price)
        if offer_price and not merged.price_high:
            merged.price_high = str(offer_price)
        return merged

    tasks = [asyncio.create_task(one(ev)) for ev in events]
    enriched = await asyncio.gather(*tasks)
    return list(enriched), errors


async def _enrich_karabas_details(
    client: httpx.AsyncClient,
    parser: KarabasParser,
    events: list[NormalizedEvent],
    timeout_seconds: float,
    max_concurrency: int,
) -> tuple[list[NormalizedEvent], list[dict[str, Any]]]:
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))
    errors: list[dict[str, Any]] = []

    async def one(ev: NormalizedEvent) -> NormalizedEvent:
        if not ev.url:
            return ev
        async with sem:
            try:
                html = await fetch_text(client, ev.url, timeout_seconds=timeout_seconds)
                details = parser.parse_detail(html)
            except Exception as exc:
                errors.append({"url": ev.url, "error": str(exc)})
                return ev

        desc_html = details.get("detail_description_html")
        if not desc_html:
            return ev

        merged = ev.model_copy(deep=True)
        merged.description = str(desc_html)
        return merged

    tasks = [asyncio.create_task(one(ev)) for ev in events]
    enriched = await asyncio.gather(*tasks)
    return list(enriched), errors


class Scraper:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self.city_index = CityIndex(repo_root=repo_root)
        self.city_index.load()
        self.karabas = KarabasParser(repo_root=repo_root)
        self.concert = ConcertParser(repo_root=repo_root)
        self.dou = DouParser(city_index=self.city_index)

    async def scrape_city(
        self,
        client: httpx.AsyncClient,
        city: str,
        req: ScrapeEventsRequest,
    ) -> tuple[list[NormalizedEvent], list[dict[str, Any]]]:
        """
        Returns (events, error_meta_list).
        """
        city = (city or "").strip()
        if not city:
            return [], [{"city": city, "error": "empty-city"}]

        events: list[NormalizedEvent] = []
        errors: list[dict[str, Any]] = []

        # karabas.com
        if "karabas.com" in req.sources:
            kc = self.city_index.resolve_karabas(city)
            url = (kc.url if kc and kc.url else None) or _guess_karabas_url(city)
            if url:
                try:
                    html = await fetch_text(client, url, timeout_seconds=req.request_timeout_seconds)
                    items = self.karabas.parse_events(html)
                    if items:
                        items, detail_errors = await _enrich_karabas_details(
                            client=client,
                            parser=self.karabas,
                            events=items,
                            timeout_seconds=req.request_timeout_seconds,
                            max_concurrency=min(12, req.concurrency * 2),
                        )
                        if detail_errors:
                            errors.append(
                                {
                                    "city": city,
                                    "source": "karabas.com",
                                    "error": "detail-fetch-errors",
                                    "count": len(detail_errors),
                                    "items": detail_errors[:20],
                                }
                            )
                    events.extend(items[: req.max_events_per_city])
                except Exception as exc:
                    errors.append({"city": city, "source": "karabas.com", "error": str(exc)})

        # concert.ua
        if "concert.ua" in req.sources:
            cc = self.city_index.resolve_concert(city)
            url = (cc.href if cc and cc.href else None) or _guess_concert_url(city)
            if url:
                try:
                    html = await fetch_text(client, url, timeout_seconds=req.request_timeout_seconds)
                    items = self.concert.parse_listing(
                        html,
                        city_slug=cc.slug if cc else None,
                        city_name=cc.name if cc else city,
                        limit=req.max_events_per_city,
                    )
                    if req.include_details and items:
                        items, detail_errors = await _enrich_concert_details(
                            client=client,
                            parser=self.concert,
                            events=items,
                            timeout_seconds=req.request_timeout_seconds,
                            max_concurrency=min(12, req.concurrency * 2),
                        )
                        if detail_errors:
                            # non-fatal; attach as meta error record
                            # (we still return events)
                            errors.append(
                                {
                                    "city": city,
                                    "source": "concert.ua",
                                    "error": "detail-fetch-errors",
                                    "count": len(detail_errors),
                                    "items": detail_errors[:20],
                                }
                            )
                    events.extend(items[: req.max_events_per_city])
                except Exception as exc:
                    errors.append({"city": city, "source": "concert.ua", "error": str(exc)})

        return events, errors

    async def scrape_all(
        self,
        req: ScrapeEventsRequest,
    ) -> tuple[list[NormalizedEvent], dict[str, Any]]:
        timeout = httpx.Timeout(req.request_timeout_seconds)
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        items: list[NormalizedEvent] = []
        errors: list[dict[str, Any]] = []

        sem = asyncio.Semaphore(req.concurrency)

        async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True) as client:
            tasks = []
            
            # City-based scrapers
            if req.cities and any(s in req.sources for s in ["karabas.com", "concert.ua"]):
                async def run_one(city: str) -> list[NormalizedEvent]:
                    async with sem:
                        city_items, errs = await self.scrape_city(client, city=city, req=req)
                        errors.extend(errs)
                        return city_items

                for c in req.cities:
                    tasks.append(asyncio.create_task(run_one(c)))
            
            # Global scrapers
            if "dou.ua" in req.sources:
                async def run_dou() -> list[NormalizedEvent]:
                    try:
                        return await self.dou.scrape_all_events(concurrency=req.concurrency)
                    except Exception as e:
                        errors.append({"source": "dou.ua", "error": str(e)})
                        return []
                tasks.append(asyncio.create_task(run_dou()))

            for t in asyncio.as_completed(tasks):
                items.extend(await t)

        meta = {
            "requested_cities": req.cities,
            "sources": req.sources,
            "include_details": req.include_details,
            "max_events_per_city": req.max_events_per_city,
            "batch_size": req.batch_size,
            "concurrency": req.concurrency,
            "total_items": len(items),
            "errors": errors,
            "generated_at": _now_iso(),
        }
        return items, meta

    async def stream_batches(
        self,
        req: ScrapeEventsRequest,
    ):
        """
        Async generator yielding NDJSON lines (bytes).
        """
        timeout = httpx.Timeout(req.request_timeout_seconds)
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)

        sem = asyncio.Semaphore(req.concurrency)
        buffer: list[NormalizedEvent] = []
        batch_index = 0
        errors: list[dict[str, Any]] = []
        total_emitted = 0

        async with httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True) as client:
            tasks = []
            
            # City-based scrapers
            if req.cities and any(s in req.sources for s in ["karabas.com", "concert.ua"]):
                async def run_one(city: str) -> list[NormalizedEvent]:
                    async with sem:
                        city_items, errs = await self.scrape_city(client, city=city, req=req)
                        errors.extend(errs)
                        return city_items

                for c in req.cities:
                    tasks.append(asyncio.create_task(run_one(c)))
            
            # Global scrapers
            if "dou.ua" in req.sources:
                async def run_dou() -> list[NormalizedEvent]:
                    try:
                        return await self.dou.scrape_all_events(concurrency=req.concurrency)
                    except Exception as e:
                        errors.append({"source": "dou.ua", "error": str(e)})
                        return []
                tasks.append(asyncio.create_task(run_dou()))

            for t in asyncio.as_completed(tasks):
                buffer.extend(await t)

                while len(buffer) >= req.batch_size:
                    chunk = buffer[: req.batch_size]
                    buffer = buffer[req.batch_size :]
                    batch = ScrapeBatch(batch_index=batch_index, items=chunk, done=False)
                    batch_index += 1
                    total_emitted += len(chunk)
                    yield (json.dumps(batch.model_dump(), ensure_ascii=False) + "\n").encode("utf-8")

        # flush remainder + done marker
        if buffer:
            batch = ScrapeBatch(batch_index=batch_index, items=buffer, done=True)
            total_emitted += len(buffer)
            yield (json.dumps(batch.model_dump(), ensure_ascii=False) + "\n").encode("utf-8")
        else:
            # still signal completion even if no items
            batch = ScrapeBatch(batch_index=batch_index, items=[], done=True)
            yield (json.dumps(batch.model_dump(), ensure_ascii=False) + "\n").encode("utf-8")

        # final meta line (optional for consumers)
        meta = {
            "type": "meta",
            "done": True,
            "requested_cities": req.cities,
            "sources": req.sources,
            "include_details": req.include_details,
            "max_events_per_city": req.max_events_per_city,
            "batch_size": req.batch_size,
            "concurrency": req.concurrency,
            "total_items_emitted": total_emitted,
            "errors": errors,
            "generated_at": _now_iso(),
        }
        yield (json.dumps(meta, ensure_ascii=False) + "\n").encode("utf-8")


