import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


ANCHOR_RE = re.compile(
    r'<a[^>]+class="([^"]*\bfiltered\b[^"]*)"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
NAME_SPAN_RE = re.compile(
    r'<span[^>]*class="[^"]*\bname\b[^"]*"[^>]*>(.*?)</span>',
    re.IGNORECASE | re.DOTALL,
)
TAGS_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class CityItem:
    name: str
    url: str
    subdomain: Optional[str]
    country: str = "Україна"
    source: str = "karabas.com"


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


def _clean_text(html_fragment: str) -> str:
    text = TAGS_RE.sub("", html_fragment)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def _extract_subdomain(url: str) -> Optional[str]:
    # Expect patterns like https://lviv.karabas.com/ or https://kyiv.karabas.com/
    m = re.match(r"^https?://([a-z0-9-]+)\.karabas\.com/?", url, flags=re.IGNORECASE)
    if not m:
        return None
    sub = m.group(1).lower()
    if sub in {"www", "karabas"}:
        return None
    return sub


def _slice_active_ua_block(html: str) -> Optional[str]:
    """
    Heuristic: find the 'one-country_tab active' block (usually Ukraine on UA domains),
    then slice from its start to the next 'one-country_tab' occurrence or end of HTML.
    """
    # Prefer the block that explicitly mentions one-country_tab active
    start_idx = html.find('class="modal-scrollable one-country_tab active"')
    if start_idx == -1:
        # fallback: a bit more permissive
        m = re.search(r'class="[^"]*\bone-country_tab\b[^"]*\bactive\b[^"]*"', html, re.IGNORECASE)
        if not m:
            return None
        start_idx = m.start()

    # Find next country tab start (end boundary), else use end of string
    next_idx = html.find('class="modal-scrollable one-country_tab', start_idx + 1)
    if next_idx == -1:
        next_idx = len(html)

    return html[start_idx:next_idx]


def parse_cities_from_html(html: str) -> List[CityItem]:
    block = _slice_active_ua_block(html) or html

    items: List[CityItem] = []
    seen_urls: set[str] = set()
    for cls, href, inner in ANCHOR_RE.findall(block):
        classes = cls.lower()
        if "ignore" in classes:
            continue
        # Extract display name, prefer <span class="name">..</span>
        nm: Optional[str] = None
        name_match = NAME_SPAN_RE.search(inner)
        if name_match:
            nm = _clean_text(name_match.group(1))
        else:
            nm = _clean_text(inner)
        if not nm:
            continue
        # Basic validation for karabas domain
        if "karabas.com" not in href:
            continue
        # De-dup by URL
        if href in seen_urls:
            continue
        seen_urls.add(href)
        items.append(
            CityItem(
                name=nm,
                url=href,
                subdomain=_extract_subdomain(href),
            )
        )

    # Filter out the generic "Усі міста" if slipped through
    items = [c for c in items if c.name != "Усі міста"]

    # Sort by name (optional, for stable output)
    items.sort(key=lambda c: c.name.lower())
    return items


def save_json(path: str, items: List[CityItem]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(i) for i in items], f, ensure_ascii=False, indent=2)


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parse Ukrainian cities from lviv.karabas.com modal.")
    group = p.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="Page URL to fetch (default: https://lviv.karabas.com/)")
    group.add_argument("--file", help="Optional local HTML file to parse")
    p.add_argument("--out", help="Output JSON path (default: karabas-cities.json)")
    p.add_argument("--no-stdout", action="store_true", help="Do not print JSON to stdout")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_cli()
    args = parser.parse_args(argv)

    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            url = args.url or "https://lviv.karabas.com/"
            html = fetch_url(url)
    except Exception as exc:
        print(f"Failed to load HTML: {exc}", file=sys.stderr)
        return 2

    try:
        cities = parse_cities_from_html(html)
    except Exception as exc:
        print(f"Failed to parse cities: {exc}", file=sys.stderr)
        return 2

    out_path = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "karabas-cities.json")

    try:
        save_json(out_path, cities)
        if not args.no_stdout:
            print(json.dumps([asdict(c) for c in cities], ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

