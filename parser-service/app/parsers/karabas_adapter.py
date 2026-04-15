from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.models import NormalizedEvent


class KarabasParser:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self._module = None

    def _load(self) -> Any:
        if self._module is not None:
            return self._module
        from app.parsers import karabas_parser
        self._module = karabas_parser
        return self._module

    def parse_events(self, html: str) -> list[NormalizedEvent]:
        m = self._load()
        # legacy function: parse_events_from_html(html) -> list[EventItem dataclass]
        items = m.parse_events_from_html(html)
        out: list[NormalizedEvent] = []
        for it in items or []:
            d = asdict(it)
            out.append(
                NormalizedEvent(
                    name=d.get("name"),
                    type=d.get("type"),
                    url=d.get("url"),
                    order_url=d.get("order_url"),
                    startDate=d.get("startDate"),
                    endDate=d.get("endDate"),
                    location_name=d.get("location_name"),
                    city=d.get("city"),
                    price_low=d.get("price_low"),
                    price_high=d.get("price_high"),
                    price_currency=d.get("price_currency"),
                    image=d.get("image"),
                    source="karabas.com",
                )
            )
        return out

    def parse_detail(self, html: str) -> dict[str, str]:
        m = self._load()
        description_html = m.extract_detail_description_html(html)
        if not description_html:
            return {}
        return {"detail_description_html": description_html}


