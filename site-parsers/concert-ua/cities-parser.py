import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


BASE_URL = "https://concert.ua"
DEFAULT_URL = "https://concert.ua/uk/kyiv"


@dataclass
class CityItem:
    name: str
    slug: Optional[str] = None
    href: Optional[str] = None
    id: Optional[str] = None
    selected: bool = False


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


def _abs_url(href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{BASE_URL}{href}"
    return f"{BASE_URL}/{href}"


def fetch_rendered_html(url: str, wait_selector: Optional[str], timeout_ms: int) -> str:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright is required for --render. Install with:\n"
            "  pip install playwright\n"
            "  python -m playwright install"
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        # Be polite; set headers similar to requests flow
        page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # If a selector is provided, wait for it (e.g., "#cityList")
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=timeout_ms)
            except Exception:
                # Continue anyway; we'll parse whatever is present
                pass
        content = page.content()
        context.close()
        browser.close()
        return content


def parse_cities_from_html(html: str) -> List[CityItem]:
    # Try to narrow down to the cities popup list first
    ul_match = re.search(
        r'<ul\s+class="[^"]*\bcity-list\b[^"]*"\s+id="cityList"\s*>(?P<body>.*?)</ul>',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    body = ul_match.group("body") if ul_match else html  # fallback: scan entire HTML

    items: List[CityItem] = []
    # Iterate over li.city-list__item (skip the "all-city__item")
    for m in re.finditer(
        r'<li[^>]*class="[^"]*\bcity-list__item\b[^"]*"(?P<li_attrs>[^>]*)>(?P<li_body>.*?)</li>',
        body,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        li_attrs = m.group("li_attrs") or ""
        li_body = m.group("li_body") or ""

        # Extract data-city slug if present
        slug_match = re.search(r'data-city="([^"]+)"', li_attrs)
        slug = slug_match.group(1) if slug_match else None

        # Extract anchor
        a_match = re.search(
            r'<a[^>]*class="([^"]*\bcity-list__link\b[^"]*)"[^>]*href="([^"]+)"[^>]*data-id="([^"]+)"[^>]*>(?P<a_body>.*?)</a>',
            li_body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not a_match:
            # Try a more tolerant variant without data-id
            a_match = re.search(
                r'<a[^>]*class="([^"]*\bcity-list__link\b[^"]*)"[^>]*href="([^"]+)"[^>]*>(?P<a_body>.*?)</a>',
                li_body,
                flags=re.DOTALL | re.IGNORECASE,
            )
        if not a_match:
            continue

        a_classes = a_match.group(1) if a_match.lastindex and a_match.lastindex >= 1 else ""
        href = a_match.group(2) if a_match.lastindex and a_match.lastindex >= 2 else None
        cid = a_match.group(3) if a_match.lastindex and a_match.lastindex >= 3 else None
        a_body = a_match.group("a_body") or ""

        # Extract city name (prefer text inside <b>...</b>)
        name_match = re.search(r"<b>\s*([^<]+?)\s*</b>", a_body, flags=re.DOTALL | re.IGNORECASE)
        if name_match:
            name = name_match.group(1).strip()
        else:
            # Fallback to stripping HTML tags from a_body
            name = re.sub(r"<[^>]+>", "", a_body).strip()
        if not name:
            continue

        selected = "selected" in (a_classes or "")
        items.append(
            CityItem(
                name=name,
                slug=slug,
                href=_abs_url(href),
                id=cid,
                selected=selected,
            )
        )

    # If nothing found inside <ul>, attempt a global fallback scan
    if not items and not ul_match:
        for m in re.finditer(
            r'<li[^>]*class="[^"]*\bcity-list__item\b[^"]*"(?P<li_attrs>[^>]*)>(?P<li_body>.*?)</li>',
            html,
            flags=re.DOTALL | re.IGNORECASE,
        ):
            li_attrs = m.group("li_attrs") or ""
            li_body = m.group("li_body") or ""
            slug_match = re.search(r'data-city="([^"]+)"', li_attrs)
            slug = slug_match.group(1) if slug_match else None
            a_match = re.search(
                r'<a[^>]*class="([^"]*\bcity-list__link\b[^"]*)"[^>]*href="([^"]+)"[^>]*(?:data-id="([^"]+)")?[^>]*>(?P<a_body>.*?)</a>',
                li_body,
                flags=re.DOTALL | re.IGNORECASE,
            )
            if not a_match:
                continue
            a_classes = a_match.group(1) or ""
            href = a_match.group(2)
            cid = a_match.group(3) if a_match.lastindex and a_match.lastindex >= 3 else None
            a_body = a_match.group("a_body") or ""
            name_match = re.search(r"<b>\s*([^<]+?)\s*</b>", a_body, flags=re.DOTALL | re.IGNORECASE)
            name = name_match.group(1).strip() if name_match else re.sub(r"<[^>]+>", "", a_body).strip()
            if not name:
                continue
            selected = "selected" in a_classes
            items.append(CityItem(name=name, slug=slug, href=_abs_url(href), id=cid, selected=selected))

    return items


def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Parse cities from concert.ua city selector popup.")
    g = p.add_mutually_exclusive_group(required=False)
    g.add_argument("--url", help="Page URL to fetch (default: https://concert.ua/uk/kyiv)")
    g.add_argument("--file", help="Path to a local HTML file for offline parsing.")
    p.add_argument(
        "--html-out",
        help="Path to write fetched HTML before parsing (default: concert-ua-page.html in script directory)",
    )
    p.add_argument("--out", help="Output JSON filename (default: concert-ua-cities.json)")
    p.add_argument("--outdir", help="Output directory (default: current script directory)")
    p.add_argument("--stdout", action="store_true", default=True, help="Print JSON to stdout.")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_cli().parse_args(argv)

    try:
        if args.file:
            with open(args.file, "r", encoding="utf-8") as f:
                html = f.read()
        else:
            url = args.url or DEFAULT_URL
            html = fetch_url(url)
            # Save raw HTML to file before parsing
            try:
                default_html_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "concert-ua-page.html")
                html_outfile = args.html_out or default_html_out
                html_outdir = os.path.dirname(os.path.abspath(html_outfile))
                if html_outdir and not os.path.exists(html_outdir):
                    os.makedirs(html_outdir, exist_ok=True)
                with open(html_outfile, "w", encoding="utf-8") as f_html:
                    f_html.write(html)
            except Exception as save_exc:
                print(f"Failed to write HTML to file: {save_exc}", file=sys.stderr)
                # Continue to parsing even if saving HTML fails
    except Exception as exc:
        print(f"Failed to load HTML: {exc}", file=sys.stderr)
        return 2

    items = parse_cities_from_html(html)

    try:
        outdir = args.outdir or os.path.dirname(os.path.abspath(__file__))
        outfile = args.out or "concert-ua-cities.json"
        if not os.path.isabs(outfile):
            outfile = os.path.join(outdir, outfile)

        # Always write file for reproducibility
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump([asdict(x) for x in items], f, ensure_ascii=False, indent=2)

        if args.stdout:
            print(json.dumps([asdict(x) for x in items], ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


