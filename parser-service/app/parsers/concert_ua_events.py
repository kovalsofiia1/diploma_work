import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from html.parser import HTMLParser

try:
    import requests  # type: ignore
except Exception:
    requests = None


BASE_URL = "https://concert.ua"
DEFAULT_CITY_LIST_FILE = "concert-ua-cities.json"
OUTPUT_EVENTS_FILE = "concert-ua-events.json"
REQUEST_TIMEOUT_SECONDS = 20
DELAY_BETWEEN_REQUESTS_SECONDS = 0.4


def _abs_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{BASE_URL}{href}"
    return f"{BASE_URL}/{href}"


def _pick_best_img_from_srcset(srcset: Optional[str]) -> Optional[str]:
    """
    Prefer the 2x candidate from srcset. Fallback to first candidate URL.
    """
    if not srcset:
        return None
    parts = [p.strip() for p in srcset.split(",") if p.strip()]
    if not parts:
        return None

    first_url: Optional[str] = None
    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        url = tokens[0]
        descriptor = tokens[1].strip().lower() if len(tokens) > 1 else ""
        if first_url is None:
            first_url = url
        if descriptor == "2x":
            return url
    return first_url


def fetch_html(url: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> str:
    if requests is None:
        raise RuntimeError("The 'requests' package is required but not installed.")
    headers = {
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
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


@dataclass
class EventItem:
    city_slug: Optional[str]
    city_name: Optional[str]
    id: Optional[str]
    href: Optional[str]
    name: Optional[str]
    date_start: Optional[str]
    categories: Optional[str]
    affiliation: Optional[str]
    currency: Optional[str]
    place: Optional[str]
    price: Optional[str]
    image: Optional[str]


class EventsHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.inside_event_anchor = False
        self.event_attrs: Dict[str, Optional[str]] = {}
        self.capture_name = False
        self.capture_place = False
        self.capture_price = False
        self.name_parts: List[str] = []
        self.place_parts: List[str] = []
        self.price_parts: List[str] = []
        self.items: List[EventItem] = []
        self.current_city_slug: Optional[str] = None
        self.current_city_name: Optional[str] = None

    def set_city(self, slug: Optional[str], name: Optional[str]) -> None:
        self.current_city_slug = slug
        self.current_city_name = name

    def handle_starttag(self, tag: str, attrs_list):
        attrs = {k.lower(): v for k, v in attrs_list}
        if tag.lower() == "a":
            class_attr = attrs.get("class", "") or ""
            if "event-card" in class_attr:
                self.inside_event_anchor = True
                self.event_attrs = {
                    "href": attrs.get("href"),
                    "id": attrs.get("data-item-id"),
                    "date_start": attrs.get("data-date-start"),
                    "categories": attrs.get("data-item-categories"),
                    "affiliation": attrs.get("data-affiliation"),
                    "currency": attrs.get("data-item-currency"),
                    "image": None,
                }
                self.name_parts = []
                self.place_parts = []
                self.price_parts = []
                return
        if self.inside_event_anchor and tag.lower() == "span":
            class_attr = (attrs.get("class") or "").strip()
            # Name
            if "event__name" in class_attr:
                self.capture_name = True
            # Place
            if "event__place" in class_attr:
                self.capture_place = True
            # Price
            if "event__price" in class_attr:
                self.capture_price = True
        if self.inside_event_anchor and tag.lower() == "img":
            # Concert.ua event cards keep preview image inside `.img-container`.
            # Capture first image URL encountered within the event anchor.
            # Prefer high-res srcset candidate marked with "2x".
            if not self.event_attrs.get("image"):
                img_srcset = attrs.get("srcset") or attrs.get("data-srcset")
                best_srcset_url = _pick_best_img_from_srcset(img_srcset)
                img_src = best_srcset_url or attrs.get("src") or attrs.get("data-src")
                self.event_attrs["image"] = _abs_url(img_src)

    def handle_endtag(self, tag: str):
        if self.inside_event_anchor and tag.lower() == "a":
            # finalize event
            href_abs = _abs_url(self.event_attrs.get("href"))
            name = " ".join(self.name_parts).strip()
            place = " ".join(self.place_parts).strip()
            price = " ".join(self.price_parts).strip()
            # normalize internal whitespace
            name = re.sub(r"\s+", " ", name) if name else None
            place = re.sub(r"\s+", " ", place) if place else None
            price = re.sub(r"\s+", " ", price) if price else None
            self.items.append(
                EventItem(
                    city_slug=self.current_city_slug,
                    city_name=self.current_city_name,
                    id=self.event_attrs.get("id"),
                    href=href_abs,
                    name=name,
                    date_start=self.event_attrs.get("date_start"),
                    categories=self.event_attrs.get("categories"),
                    affiliation=self.event_attrs.get("affiliation"),
                    currency=self.event_attrs.get("currency"),
                    place=place,
                    price=price,
                    image=self.event_attrs.get("image"),
                )
            )
            # reset flags
            self.inside_event_anchor = False
            self.event_attrs = {}
            self.capture_name = False
            self.capture_place = False
            self.capture_price = False
            self.name_parts = []
            self.place_parts = []
            self.price_parts = []
        elif self.inside_event_anchor and tag.lower() == "span":
            # stop captures at closing span
            self.capture_name = False
            self.capture_place = False
            self.capture_price = False

    def handle_data(self, data: str):
        if not self.inside_event_anchor:
            return
        if self.capture_name:
            self.name_parts.append(data)
        if self.capture_place:
            self.place_parts.append(data)
        if self.capture_price:
            self.price_parts.append(data)


def parse_events_from_html(html: str, city_slug: Optional[str], city_name: Optional[str]) -> List[EventItem]:
    parser = EventsHTMLParser()
    parser.set_city(city_slug, city_name)
    parser.feed(html)
    primary_items = parser.items

    # Fallback for pages where card markup differs but JSON-LD is present.
    jsonld_items = _parse_events_from_jsonld(html, city_slug=city_slug, city_name=city_name)
    if not jsonld_items:
        return primary_items

    merged: List[EventItem] = []
    seen: set[tuple[Optional[str], Optional[str], Optional[str]]] = set()

    def add_item(item: EventItem) -> None:
        key = (item.href, item.name, item.date_start)
        if key in seen:
            return
        seen.add(key)
        merged.append(item)

    for item in primary_items:
        add_item(item)
    for item in jsonld_items:
        add_item(item)

    return merged


def _extract_jsonld_objects(html: str) -> List[Any]:
    out: List[Any] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(?P<json>.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        raw = (m.group("json") or "").strip()
        if not raw:
            continue
        raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("\u0000", "")
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def _is_event_type(value: Any) -> bool:
    if isinstance(value, list):
        return any(_is_event_type(v) for v in value)
    if isinstance(value, str):
        t = value.casefold()
        return t in {"event", "musicevent"}
    return False


def _jsonld_event_nodes(objects: List[Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []

    def maybe_add(obj: Any) -> None:
        if isinstance(obj, dict) and _is_event_type(obj.get("@type")):
            nodes.append(obj)

    for root in objects:
        if isinstance(root, dict):
            graph = root.get("@graph")
            if isinstance(graph, list):
                for g in graph:
                    maybe_add(g)
            else:
                maybe_add(root)
        elif isinstance(root, list):
            for item in root:
                if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                    for g in item["@graph"]:
                        maybe_add(g)
                else:
                    maybe_add(item)
    return nodes


def _normalize_offers(offers: Any) -> List[Dict[str, Any]]:
    if isinstance(offers, dict):
        return [offers]
    if isinstance(offers, list):
        return [o for o in offers if isinstance(o, dict)]
    return []


def _parse_events_from_jsonld(html: str, city_slug: Optional[str], city_name: Optional[str]) -> List[EventItem]:
    objects = _extract_jsonld_objects(html)
    nodes = _jsonld_event_nodes(objects)
    out: List[EventItem] = []

    for node in nodes:
        name = str(node.get("name") or "").strip() or None
        href = _abs_url(str(node.get("url") or "").strip()) if node.get("url") else None
        date_start = str(node.get("startDate") or "").strip() or None

        location = node.get("location") if isinstance(node.get("location"), dict) else {}
        place = str(location.get("name") or "").strip() or None

        offers = _normalize_offers(node.get("offers"))
        first_offer = offers[0] if offers else {}
        currency = str(first_offer.get("priceCurrency") or "").strip() or None
        price = str(first_offer.get("price") or "").strip() or None
        if price and currency:
            price = f"від {price} {currency}"

        image_raw = node.get("image")
        if isinstance(image_raw, list):
            image_raw = image_raw[0] if image_raw else None
        image = _abs_url(str(image_raw).strip()) if image_raw else None

        if not (name and href):
            continue

        out.append(
            EventItem(
                city_slug=city_slug,
                city_name=city_name,
                id=None,
                href=href,
                name=name,
                date_start=date_start,
                categories=None,
                affiliation=None,
                currency=currency,
                place=place,
                price=price,
                image=image,
            )
        )
    return out


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cities_path = os.path.join(base_dir, DEFAULT_CITY_LIST_FILE)
    if not os.path.exists(cities_path):
        print(f"Cities JSON not found: {cities_path}", file=sys.stderr)
        return 2
    try:
        with open(cities_path, "r", encoding="utf-8") as f:
            cities_raw = json.load(f)
    except Exception as exc:
        print(f"Failed to read cities JSON: {exc}", file=sys.stderr)
        return 2

    # Normalize to dicts
    cities: List[Dict[str, Optional[str]]] = []
    for c in cities_raw:
        if isinstance(c, dict):
            cities.append(c)

    all_events: List[Dict[str, Optional[str]]] = []
    for idx, city in enumerate(cities, start=1):
        city_slug = city.get("slug")
        city_name = city.get("name")
        href = city.get("href")
        url = _abs_url(href) if href else None
        if not url:
            continue
        try:
            html = fetch_html(url)
        except Exception as exc:
            print(f"[{idx}/{len(cities)}] {city_name or city_slug}: fetch failed: {exc}", file=sys.stderr)
            continue

        events = parse_events_from_html(html, city_slug=city_slug, city_name=city_name)
        all_events.extend([asdict(e) for e in events])
        print(f"[{idx}/{len(cities)}] {city_name or city_slug}: {len(events)} events")
        time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

    out_path = os.path.join(base_dir, OUTPUT_EVENTS_FILE)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(all_events)} events to {out_path}")
    except Exception as exc:
        print(f"Failed to write events JSON: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


