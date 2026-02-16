import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

try:
    import requests  # type: ignore
except Exception:
    requests = None


BASE_URL = "https://concert.ua"
DEFAULT_URL = "https://concert.ua/uk/event/laud"
DEFAULT_HTML_OUT = "single-event-page.html"
DEFAULT_JSON_OUT = "single-event-details.json"


def _abs_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{BASE_URL}{href}"
    return f"{BASE_URL}/{href}"


def fetch_html(url: str, timeout: int = 20) -> str:
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


def extract_jsonld_objects(html: str) -> List[Any]:
    results: List[Any] = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(?P<json>.*?)</script>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        raw = (m.group("json") or "").strip()
        raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("\u0000", "")
        try:
            data = json.loads(raw)
            results.append(data)
        except Exception:
            raw2 = raw.strip(" \n\r\t/*")
            try:
                data2 = json.loads(raw2)
                results.append(data2)
            except Exception:
                continue
    return results


def _is_event_type(t: Any) -> bool:
    if isinstance(t, list):
        return any(str(x).lower() in ("event", "musicevent") for x in t)
    if isinstance(t, str):
        return t.lower() in ("event", "musicevent")
    return False


def find_event_nodes(jsonlds: List[Any]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    def maybe_add(obj: Any) -> None:
        if isinstance(obj, dict) and _is_event_type(obj.get("@type")):
            nodes.append(obj)
    for root in jsonlds:
        if isinstance(root, dict):
            graph = root.get("@graph")
            if isinstance(graph, list):
                for x in graph:
                    maybe_add(x)
            else:
                maybe_add(root)
        elif isinstance(root, list):
            for x in root:
                if isinstance(x, dict) and "@graph" in x and isinstance(x["@graph"], list):
                    for y in x["@graph"]:
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
    elif isinstance(perf, dict) and perf.get("name"):
        performers.append(str(perf.get("name")))
    elif isinstance(perf, str):
        performers.append(perf)
    if performers:
        details["performers"] = performers
    # Organizer
    org = node.get("organizer")
    if isinstance(org, dict) and org.get("name"):
        details["organizer_name"] = org.get("name")
    elif isinstance(org, str):
        details["organizer_name"] = org
    return details


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Fetch one event page, save HTML, parse JSON-LD details.")
    p.add_argument("--url", help="Event page URL (default: concert.ua The Maneken)", default=None)
    p.add_argument("--html-out", help="Where to save fetched HTML", default=None)
    p.add_argument("--json-out", help="Where to save parsed details JSON", default=None)
    return p


def main(argv: Optional[list] = None) -> int:
    args = build_cli().parse_args(argv)
    url = args.url or DEFAULT_URL
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_out = args.html_out or os.path.join(base_dir, DEFAULT_HTML_OUT)
    json_out = args.json_out or os.path.join(base_dir, DEFAULT_JSON_OUT)

    try:
        html = fetch_html(url)
    except Exception as exc:
        print(f"Failed to fetch page: {exc}", file=sys.stderr)
        return 2

    # Save raw HTML
    try:
        outdir = os.path.dirname(os.path.abspath(html_out))
        if outdir and not os.path.exists(outdir):
            os.makedirs(outdir, exist_ok=True)
        with open(html_out, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as exc:
        print(f"Failed to write HTML file: {exc}", file=sys.stderr)
        # keep going to parse

    jsonlds = extract_jsonld_objects(html)
    nodes = find_event_nodes(jsonlds)
    result: Dict[str, Any] = {"source_url": url}
    if nodes:
        details = extract_details_from_event_node(nodes[0])
        result.update(details)
    else:
        result["_error"] = "no-jsonld-event-found"

    try:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Wrote details to {json_out}")
    except Exception as exc:
        print(f"Failed to write JSON: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


