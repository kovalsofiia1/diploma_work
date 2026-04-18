from __future__ import annotations

import re
from typing import Any, Optional

from app.models import NormalizedEvent


def _abs_concert_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"https://concert.ua{href}"
    return f"https://concert.ua/{href}"


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
            
            # Concert.ua booking URL is usually the event URL but with /booking/ instead of /event/
            event_url = d.get("href")
            order_url = None
            if event_url:
                if "/event/" in event_url:
                    order_url = event_url.replace("/event/", "/booking/")
                elif "/uk/" in event_url:
                    # Fallback for URLs like https://concert.ua/uk/blagodiinii-stendap
                    parts = event_url.split("/uk/")
                    if len(parts) > 1:
                        order_url = f"{parts[0]}/uk/booking/{parts[1]}"
                if not order_url:
                    order_url = event_url
                
            out.append(
                NormalizedEvent(
                    name=_norm_space(d.get("name") or "") or None,
                    type=_norm_space(d.get("categories") or "") or None,
                    url=event_url,
                    order_url=order_url,
                    startDate=d.get("date_start"),
                    endDate=None,
                    location_name=_norm_space(d.get("place") or "") or None,
                    city=city_name,
                    price_low=low,
                    price_high=high,
                    price_currency=cur or _norm_space(d.get("currency") or "") or None,
                    image=d.get("image"),
                    source="concert.ua",
                )
            )
        return out

    def parse_ajax_listing(
        self,
        ajax_items: list[dict[str, Any]],
        city_name: str | None,
        limit: int,
    ) -> list[NormalizedEvent]:
        out: list[NormalizedEvent] = []
        for item in (ajax_items or [])[: max(0, int(limit))]:
            if not isinstance(item, dict):
                continue

            event_url = _abs_concert_url(str(item.get("link") or "").strip() or None)
            order_url = None
            if event_url:
                if "/event/" in event_url:
                    order_url = event_url.replace("/event/", "/booking/")
                elif "/events/" in event_url:
                    order_url = event_url.replace("/events/", "/booking/")
                elif "/uk/" in event_url:
                    parts = event_url.split("/uk/")
                    if len(parts) > 1:
                        order_url = f"{parts[0]}/uk/booking/{parts[1]}"
                if not order_url:
                    order_url = event_url

            categories = item.get("categoriesTitles")
            category_text = None
            if isinstance(categories, list):
                category_text = ", ".join(_norm_space(str(x)) for x in categories if str(x).strip()) or None

            venue_titles = item.get("venuesTitles")
            location_name = None
            if isinstance(venue_titles, list) and venue_titles:
                location_name = _norm_space(str(venue_titles[0])) or None

            city_titles = item.get("venuesCitiesTitles")
            city_value = city_name
            if isinstance(city_titles, list) and city_titles:
                city_value = _norm_space(str(city_titles[0])) or city_name

            price_min = item.get("priceMin")
            price = str(price_min) if price_min is not None else None

            out.append(
                NormalizedEvent(
                    name=_norm_space(str(item.get("title") or "")) or None,
                    type=category_text,
                    url=event_url,
                    order_url=order_url,
                    startDate=str(item.get("dateStart") or "").strip() or None,
                    endDate=str(item.get("dateEnd") or "").strip() or None,
                    location_name=location_name,
                    city=city_value,
                    price_low=price,
                    price_high=price,
                    price_currency=_norm_space(str(item.get("currency") or "")) or None,
                    image=_abs_concert_url(str(item.get("posterUrl") or "").strip() or None),
                    source="concert.ua",
                )
            )
        return out

    def parse_detail(self, html: str) -> dict[str, Any]:
        self._ensure_imports()
        jsonlds = self._detail_mod.extract_jsonld_objects(html)  # type: ignore[attr-defined]
        nodes = self._detail_mod.find_event_nodes(jsonlds)  # type: ignore[attr-defined]
        from bs4 import BeautifulSoup

        details = {}
        if nodes:
            details = self._detail_mod.extract_details_from_event_node(nodes[0])  # type: ignore[attr-defined]

        soup = BeautifulSoup(html, "html.parser")

        # Some pages return empty HTML containers in JSON-LD description.
        # Treat those as missing descriptions and continue with HTML fallbacks.
        current_desc = details.get("detail_description")
        if isinstance(current_desc, str):
            current_desc_text = BeautifulSoup(current_desc, "html.parser").get_text(" ", strip=True)
            if not current_desc_text:
                details.pop("detail_description", None)

        # Prefer popup description HTML because it preserves concert.ua formatting.
        popup = soup.select_one(".popup-overlay.popup-event-info")
        popup_desc = None
        if popup:
            popup_desc = popup.select_one("#event-info") or popup.select_one(".event-description")
        if popup_desc:
            for node in popup_desc.select("script, style, noscript"):
                node.decompose()
            popup_html = "".join(str(child) for child in popup_desc.contents).strip()
            popup_text = popup_desc.get_text(" ", strip=True)
            if popup_html and popup_text:
                details["detail_description"] = popup_html
                return details

        # Fallback to non-popup event description.
        desc_div = soup.find("div", class_="event-description")
        if desc_div and not details.get("detail_description"):
            fallback_html = "".join(str(child) for child in desc_div.contents).strip()
            fallback_text = desc_div.get_text(" ", strip=True)
            if fallback_text:
                details["detail_description"] = fallback_html or fallback_text

        # Extract more detailed venue address from popup info block.
        if popup:
            venue_info = popup.select_one("#venue-info")
            if venue_info:
                venue_row = venue_info.select_one("div.display-flex.align-items-center.gap-6")
                if venue_row:
                    venue_col = venue_row.select_one("span.display-flex.flex-direction-column")
                    if venue_col:
                        venue_parts = venue_col.find_all("span", recursive=False)
                        venue_name = (
                            venue_parts[0].get_text(" ", strip=True) if len(venue_parts) > 0 else ""
                        )
                        venue_address = (
                            venue_parts[1].get_text(" ", strip=True) if len(venue_parts) > 1 else ""
                        )

                        if venue_name and venue_address:
                            details["location_name"] = f"{venue_name}, {venue_address}"
                        elif venue_name:
                            details["location_name"] = venue_name

                        if venue_address and not details.get("address_street"):
                            details["address_street"] = venue_address

                        # Try to infer city from address like "Стрий, вул. Стрийська 10д".
                        if venue_address and not details.get("address_locality"):
                            locality = venue_address.split(",", 1)[0].strip()
                            if locality:
                                details["address_locality"] = locality
                
        return details


