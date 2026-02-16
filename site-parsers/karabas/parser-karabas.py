import argparse
import csv
import json
import re
import sys
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # Fallback if requests is not installed; URL fetching will be disabled


JSON_LD_SCRIPT_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class EventItem:
    name: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    order_url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    price_low: Optional[str] = None
    price_high: Optional[str] = None
    price_currency: Optional[str] = None
    image: Optional[str] = None
    source: str = "karabas.com"


def _safe_get(d: Dict[str, Any], path: Iterable[str]) -> Optional[Any]:
    current: Any = d
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def extract_json_ld_objects(html: str) -> List[Dict[str, Any]]:
    blocks = JSON_LD_SCRIPT_RE.findall(html)
    objects: List[Dict[str, Any]] = []
    for raw in blocks:
        content = raw.strip()
        if not content:
            continue
        # Some pages may wrap multiple objects or include comments; try to parse carefully
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Attempt to recover by extracting JSON-like content between first and last braces
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    continue
            else:
                continue
        # JSON-LD may be a single object or an array of objects
        if isinstance(parsed, dict):
            objects.append(parsed)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    objects.append(item)
    return objects


def map_json_ld_to_event(obj: Dict[str, Any]) -> Optional[EventItem]:
    # Minimal required keys
    name = obj.get("name")
    url = obj.get("url")
    start_date = obj.get("startDate")

    # Offers block
    offers = obj.get("offers") if isinstance(obj.get("offers"), dict) else None
    order_url = _safe_get(obj, ["offers", "url"])
    price_low = _safe_get(obj, ["offers", "lowPrice"])
    price_high = _safe_get(obj, ["offers", "highPrice"])
    price_currency = _safe_get(obj, ["offers", "priceCurrency"])

    # Location block
    location_name = _safe_get(obj, ["location", "name"])
    city = _safe_get(obj, ["location", "address", "addressLocality"])

    image = obj.get("image")
    end_date = obj.get("endDate")

    # Event type may vary (MusicEvent, TheaterEvent, etc.)
    event_type = obj.get("@type")

    # If it doesn't look like an event, skip
    if not (name and url and start_date):
        # Some JSON-LD blocks on the page may not describe events
        return None

    return EventItem(
        name=str(name) if name is not None else None,
        type=str(event_type) if event_type is not None else None,
        url=str(url) if url is not None else None,
        order_url=str(order_url) if order_url is not None else None,
        startDate=str(start_date) if start_date is not None else None,
        endDate=str(end_date) if end_date is not None else None,
        location_name=str(location_name) if location_name is not None else None,
        city=str(city) if city is not None else None,
        price_low=str(price_low) if price_low is not None else None,
        price_high=str(price_high) if price_high is not None else None,
        price_currency=str(price_currency) if price_currency is not None else None,
        image=str(image) if image is not None else None,
    )


def parse_events_from_html(html: str) -> List[EventItem]:
    json_ld_objects = extract_json_ld_objects(html)
    events: List[EventItem] = []
    for obj in json_ld_objects:
        evt = map_json_ld_to_event(obj)
        if evt is not None:
            events.append(evt)
    return events


def fetch_url(url: str, timeout: int = 20) -> str:
    if requests is None:
        raise RuntimeError("The 'requests' package is required to fetch URLs but is not installed.")
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


def save_json(path: str, events: List[EventItem]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in events], f, ensure_ascii=False, indent=2)


def save_csv(path: str, events: List[EventItem]) -> None:
    fieldnames = [
        "name",
        "type",
        "url",
        "order_url",
        "startDate",
        "endDate",
        "location_name",
        "city",
        "price_low",
        "price_high",
        "price_currency",
        "image",
        "source",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in events:
            writer.writerow(asdict(e))


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Parse events from karabas.com listing pages (via JSON-LD)."
    )
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="Page URL to fetch and parse (e.g., https://karabas.com/)")
    group.add_argument(
        "--file",
        help="Path to a local HTML file to parse (e.g., page-example.html).",
        default="page-example.html",
    )
    p.add_argument(
        "--outdir",
        help="Directory to write output files into (defaults to current script directory).",
        default=None,
    )
    p.add_argument("--json", help="Write parsed events to a JSON file.")
    p.add_argument("--csv", help="Write parsed events to a CSV file.")
    p.add_argument(
        "--stdout",
        help="Print parsed events as JSON to stdout.",
        action="store_true",
        default=True,
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    try:
        if args.url:
            html = fetch_url(args.url)
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                html = f.read()
    except Exception as exc:
        print(f"Failed to load HTML: {exc}", file=sys.stderr)
        return 2

    events = parse_events_from_html(html)

    # Outputs
    try:
        # Resolve output directory (defaults to this script directory when not provided)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        outdir = args.outdir if args.outdir is not None else script_dir

        if args.json:
            json_path = args.json if os.path.isabs(args.json) else os.path.join(outdir, args.json)
            save_json(json_path, events)
        if args.csv:
            csv_path = args.csv if os.path.isabs(args.csv) else os.path.join(outdir, args.csv)
            save_csv(csv_path, events)
        # If no explicit outputs requested, also write to karabas-events.json in this folder
        if not args.json and not args.csv:
            default_path = os.path.join(outdir, "karabas-events.json")
            save_json(default_path, events)
        if args.stdout or (not args.json and not args.csv):
            print(json.dumps([asdict(e) for e in events], ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

