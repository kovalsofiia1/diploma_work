import json
import os
import re
import sys
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

try:
    import requests  # type: ignore
except Exception:
    requests = None


BASE_URL = "https://concert.ua"
INPUT_EVENTS_FILE = "concert-ua-events.json"
OUTPUT_DETAILS_FILE = "concert-ua-event-details.json"
DETAIL_PAGES_DIR = "concert-ua-event-pages"
REQUEST_TIMEOUT_SECONDS = 20
DELAY_BETWEEN_REQUESTS_SECONDS = 0.35


def _abs_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{BASE_URL}{href}"
    return f"{BASE_URL}/{href}"


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


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-")
    return cleaned or hashlib.sha1(name.encode("utf-8", errors="ignore")).hexdigest()[:16]


def compute_event_filename(event: Dict[str, Any]) -> str:
    event_id = (event.get("id") or "").strip()
    if event_id:
        return f"{event_id}.html"
    href = event.get("href") or ""
    if href:
        tail = href.split("/")[-1] or "event"
        return f"{_safe_filename(tail)}.html"
    # fallback to hash of event JSON
    h = hashlib.sha1(json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return f"{h}.html"


def save_event_page(event: Dict[str, Any], base_dir: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (file_path, error_message). If error_message is not None, saving failed.
    """
    url = _abs_url(event.get("href"))
    if not url:
        return None, "missing href"
    pages_dir = os.path.join(base_dir, DETAIL_PAGES_DIR)
    ensure_dir(pages_dir)
    filename = compute_event_filename(event)
    filepath = os.path.join(pages_dir, filename)
    try:
        # Skip download if file already exists
        if not os.path.exists(filepath):
            html = fetch_html(url)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)
            time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)
        return filepath, None
    except Exception as exc:
        return None, str(exc)


def extract_jsonld_objects(html: str) -> List[Any]:
    """
    Extract JSON-LD objects from the HTML. Handles both single object and array payloads.
    """
    results: List[Any] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(?P<json>.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        raw = (m.group("json") or "").strip()
        # Some sites HTML-encode chars; attempt to unescape common entities
        raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("\u0000", "")
        try:
            data = json.loads(raw)
            results.append(data)
        except Exception:
            # Try to locate JSON object within potential surrounding whitespace/comments
            raw2 = raw.strip(" \n\r\t/*")
            try:
                data2 = json.loads(raw2)
                results.append(data2)
            except Exception:
                continue
    return results


def find_event_nodes(jsonlds: List[Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    def maybe_add(obj: Any) -> None:
        if isinstance(obj, dict):
            t = obj.get("@type")
            if isinstance(t, list):
                types = [str(x).lower() for x in t]
                if "event" in types or "musicevent" in types:
                    nodes.append(obj)
            elif isinstance(t, str):
                t_low = t.lower()
                if t_low in ("event", "musicevent"):
                    nodes.append(obj)
    for root in jsonlds:
        if isinstance(root, dict):
            # Some pages nest under @graph
            graph = root.get("@graph")
            if isinstance(graph, list):
                for x in graph:
                    maybe_add(x)
            else:
                maybe_add(root)
        elif isinstance(root, list):
            for x in root:
                if isinstance(x, dict):
                    # Could be a @graph-style array
                    graph = x.get("@graph") if isinstance(x, dict) else None
                    if isinstance(graph, list):
                        for y in graph:
                            maybe_add(y)
                    else:
                        maybe_add(x)
    return nodes


def normalize_offers(offers: Any) -> List[Dict[str, Any]]:
    if not offers:
        return []
    if isinstance(offers, list):
        return [o for o in offers if isinstance(o, dict)]
    if isinstance(offers, dict):
        return [offers]
    return []


def extract_details_from_event_node(node: Dict[str, Any]) -> Dict[str, Any]:
    details: Dict[str, Any] = {}
    details["detail_name"] = node.get("name")
    details["detail_description"] = node.get("description")
    details["start_date_iso"] = node.get("startDate")
    details["end_date_iso"] = node.get("endDate")
    # Location
    loc = node.get("location") if isinstance(node.get("location"), dict) else None
    if loc:
        details["location_name"] = loc.get("name")
        address = loc.get("address") if isinstance(loc.get("address"), dict) else None
        if address:
            details["address_locality"] = address.get("addressLocality")
            details["address_street"] = address.get("streetAddress")
            details["address_country"] = address.get("addressCountry")
    # Offers
    offers = normalize_offers(node.get("offers"))
    if offers:
        first = offers[0]
        details["offer_price"] = first.get("price")
        details["offer_currency"] = first.get("priceCurrency")
        details["offer_availability"] = first.get("availability")
        details["offer_url"] = first.get("url")
    # Performers
    perf = node.get("performer")
    performers: List[str] = []
    if isinstance(perf, list):
        for p in perf:
            if isinstance(p, dict) and p.get("name"):
                performers.append(str(p.get("name")))
            elif isinstance(p, str):
                performers.append(p)
    elif isinstance(perf, dict):
        if perf.get("name"):
            performers.append(str(perf.get("name")))
    elif isinstance(perf, str):
        performers.append(perf)
    if performers:
        details["performers"] = performers
    # Organizer
    org = node.get("organizer")
    if isinstance(org, dict):
        details["organizer_name"] = org.get("name")
    elif isinstance(org, str):
        details["organizer_name"] = org
    return details


def parse_event_detail_html(html: str) -> Dict[str, Any]:
    jsonlds = extract_jsonld_objects(html)
    nodes = find_event_nodes(jsonlds)
    if not nodes:
        return {"_error": "no-jsonld-event-found"}
    # Prefer the first event-like node
    return extract_details_from_event_node(nodes[0])


def main() -> int:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    events_path = os.path.join(base_dir, INPUT_EVENTS_FILE)
    if not os.path.exists(events_path):
        print(f"Events JSON not found: {events_path}", file=sys.stderr)
        return 2
    try:
        with open(events_path, "r", encoding="utf-8") as f:
            events = json.load(f)
    except Exception as exc:
        print(f"Failed to read events JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(events, list):
        print("Events JSON should be a list.", file=sys.stderr)
        return 2

    enriched: List[Dict[str, Any]] = []
    total = len(events)
    pages_dir = os.path.join(base_dir, DETAIL_PAGES_DIR)
    ensure_dir(pages_dir)

    for idx, ev in enumerate(events, start=1):
        if not isinstance(ev, dict):
            continue
        url = _abs_url(ev.get("href"))
        if not url:
            merged = dict(ev)
            merged.update({"detail_html_path": None, "_detail_error": "missing href"})
            enriched.append(merged)
            print(f"[{idx}/{total}] missing href: {ev.get('name') or ev.get('id')}", file=sys.stderr)
            continue
        # Fetch HTML and parse in-memory first
        try:
            html = fetch_html(url)
        except Exception as exc:
            merged = dict(ev)
            merged.update({"detail_html_path": None, "_detail_error": f"download-failed: {exc}"})
            enriched.append(merged)
            print(f"[{idx}/{total}] download failed: {ev.get('name') or ev.get('id')}: {exc}", file=sys.stderr)
            continue
        details = parse_event_detail_html(html)
        # Save HTML to file for reference (do not use it for parsing)
        filename = compute_event_filename(ev)
        path = os.path.join(pages_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as exc:
            # Non-fatal: keep details even if saving HTML fails
            print(f"[{idx}/{total}] warning: failed to save HTML for {ev.get('name') or ev.get('id')}: {exc}", file=sys.stderr)
        merged = dict(ev)
        merged.update(details)
        merged["detail_html_path"] = path
        enriched.append(merged)
        # progress
        print(f"[{idx}/{total}] parsed details: {ev.get('name') or ev.get('id')}")
        time.sleep(DELAY_BETWEEN_REQUESTS_SECONDS)

    out_path = os.path.join(base_dir, OUTPUT_DETAILS_FILE)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, ensure_ascii=False, indent=2)
        print(f"Wrote details for {len(enriched)} events to {out_path}")
    except Exception as exc:
        print(f"Failed to write details JSON: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


