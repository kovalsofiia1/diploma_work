import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional
from html.parser import HTMLParser

try:
    import requests  # type: ignore
except Exception:
    requests = None


BASE_URL = "https://concert.ua"
PAGE_URL = "https://concert.ua/uk/kyiv"


@dataclass
class CityItem:
    name: str
    slug: Optional[str] = None
    href: Optional[str] = None
    id: Optional[str] = None
    selected: bool = False


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


def parse_cities_from_html(html: str) -> List[CityItem]:
    class CityListHTMLParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=True)
            self.inside_city_ul = False
            self.ul_depth = 0
            self.inside_city_li = False
            self.current_city_slug: Optional[str] = None
            self.inside_anchor = False
            self.anchor_classes: str = ""
            self.anchor_href: Optional[str] = None
            self.anchor_id: Optional[str] = None
            self.anchor_text_parts: List[str] = []
            self.items: List[CityItem] = []

        def handle_starttag(self, tag: str, attrs_list):
            attrs = {k.lower(): v for k, v in attrs_list}
            if tag.lower() == "ul":
                if not self.inside_city_ul and attrs.get("id", "").lower() == "citylist":
                    self.inside_city_ul = True
                    self.ul_depth = 1
                elif self.inside_city_ul:
                    self.ul_depth += 1
                return
            if self.inside_city_ul:
                if tag.lower() == "li":
                    class_attr = attrs.get("class", "") or ""
                    if "city-list__item" in class_attr:
                        self.inside_city_li = True
                        self.current_city_slug = attrs.get("data-city")
                if self.inside_city_li and tag.lower() == "a":
                    self.inside_anchor = True
                    self.anchor_classes = attrs.get("class", "") or ""
                    self.anchor_href = attrs.get("href")
                    self.anchor_id = attrs.get("data-id")
                    self.anchor_text_parts = []
            # nested <b> etc. are handled via data events

        def handle_endtag(self, tag: str):
            if tag.lower() == "ul" and self.inside_city_ul:
                self.ul_depth -= 1
                if self.ul_depth <= 0:
                    self.inside_city_ul = False
            if self.inside_city_ul and tag.lower() == "a" and self.inside_anchor:
                # finalize current anchor if we are inside a city li
                text = "".join(self.anchor_text_parts).strip()
                # strip any remaining tags text might have accumulated
                text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()
                if text and self.inside_city_li:
                    self.items.append(
                        CityItem(
                            name=text,
                            slug=self.current_city_slug,
                            href=_abs_url(self.anchor_href),
                            id=self.anchor_id,
                            selected=("selected" in (self.anchor_classes or "")),
                        )
                    )
                self.inside_anchor = False
                self.anchor_classes = ""
                self.anchor_href = None
                self.anchor_id = None
                self.anchor_text_parts = []
            if self.inside_city_ul and tag.lower() == "li" and self.inside_city_li:
                self.inside_city_li = False
                self.current_city_slug = None

        def handle_data(self, data: str):
            if self.inside_anchor:
                self.anchor_text_parts.append(data)

    parser = CityListHTMLParser()
    parser.feed(html)
    return parser.items


def main() -> int:
    # Prefer parsing from the saved local HTML file next to this script
    items: List[CityItem] = []
    local_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "concert-ua-page.html")
    if os.path.exists(local_file):
        try:
            with open(local_file, "r", encoding="utf-8") as f:
                html_local = f.read()
            items = parse_cities_from_html(html_local)
        except Exception as exc:
            print(f"Failed to parse local file: {exc}", file=sys.stderr)
            items = []
    # If local file is missing, fall back to live fetch
    if not items and not os.path.exists(local_file):
        try:
            html = fetch_html(PAGE_URL)
            items = parse_cities_from_html(html)
        except Exception as exc:
            print(f"Failed to fetch page: {exc}", file=sys.stderr)

    outdir = os.path.dirname(os.path.abspath(__file__))
    outfile = os.path.join(outdir, "concert-ua-cities.json")
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump([asdict(x) for x in items], f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(items)} cities to {outfile}")
    except Exception as exc:
        print(f"Failed to write output: {exc}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


