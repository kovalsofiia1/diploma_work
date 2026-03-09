from __future__ import annotations

import re
from typing import Any, Optional

from app.models import NormalizedEvent


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _parse_price_text(price_text: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Very tolerant parser: extracts numbers and tries to guess currency.
    Returns (low, high, currency).
    """
    if not price_text:
        return None, None, None
    t = price_text
    currency = None
    if "uah" in t.casefold() or "грн" in t.casefold():
        currency = "UAH"
    # extract numbers (may be integers)
    nums = re.findall(r"(\d{1,6})", t.replace("\xa0", " "))
    if not nums:
        return None, None, currency
    if len(nums) == 1:
        return nums[0], nums[0], currency
    return nums[0], nums[1], currency


class ConcertParser:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self._events_mod = None
        self._detail_mod = None

    def _ensure_imports(self) -> None:
        if self._events_mod is not None and self._detail_mod is not None:
            return

        from app.parsers import concert_ua_events
        from app.parsers import concert_ua_detail

        self._events_mod = concert_ua_events
        self._detail_mod = concert_ua_detail

    def parse_listing(self, html: str, city_slug: str | None, city_name: str | None, limit: int) -> list[NormalizedEvent]:
        self._ensure_imports()
        items = self._events_mod.parse_events_from_html(html, city_slug=city_slug, city_name=city_name)  # type: ignore[attr-defined]
        out: list[NormalizedEvent] = []
        for it in (items or [])[: max(0, int(limit))]:
            # it is a dataclass from legacy module
            d = getattr(it, "__dict__", None) or {}
            low, high, cur = _parse_price_text(d.get("price"))
            out.append(
                NormalizedEvent(
                    name=_norm_space(d.get("name") or "") or None,
                    type=_norm_space(d.get("categories") or "") or None,
                    url=d.get("href"),
                    order_url=None,
                    startDate=d.get("date_start"),
                    endDate=None,
                    location_name=_norm_space(d.get("place") or "") or None,
                    city=city_name,
                    price_low=low,
                    price_high=high,
                    price_currency=cur or _norm_space(d.get("currency") or "") or None,
                    image=None,
                    source="concert.ua",
                )
            )
        return out

    def parse_detail(self, html: str) -> dict[str, Any]:
        self._ensure_imports()
        jsonlds = self._detail_mod.extract_jsonld_objects(html)  # type: ignore[attr-defined]
        nodes = self._detail_mod.find_event_nodes(jsonlds)  # type: ignore[attr-defined]
        if not nodes:
            return {}
        return self._detail_mod.extract_details_from_event_node(nodes[0])  # type: ignore[attr-defined]


