from __future__ import annotations

import json
import os
from dataclasses import dataclass


def _norm_city_key(value: str) -> str:
    # Very lightweight normalization; keep it predictable
    return " ".join((value or "").strip().casefold().split())


@dataclass(frozen=True)
class ConcertCity:
    name: str
    slug: str | None
    href: str | None


@dataclass(frozen=True)
class KarabasCity:
    name: str
    subdomain: str | None
    url: str | None


class CityIndex:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self._concert_by_key: dict[str, ConcertCity] = {}
        self._karabas_by_key: dict[str, KarabasCity] = {}

    @staticmethod
    def _load_json(path: str) -> object:
        # These JSON files in this repo may be saved as cp1251 (even if they look like UTF-8 files).
        # Try a few common encodings to avoid "���" city names.
        last_exc: Exception | None = None
        for enc in ("utf-8", "utf-8-sig", "cp1251"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return json.load(f)
            except Exception as exc:  # pragma: no cover
                last_exc = exc
                continue
        raise RuntimeError(f"Failed to load JSON {path}: {last_exc}")

    def load(self) -> None:
        # Load local JSON files
        base_dir = os.path.dirname(__file__)
        concert_path = os.path.join(base_dir, "concert-ua-cities.json")
        karabas_path = os.path.join(base_dir, "karabas-cities.json")

        if os.path.exists(concert_path):
            raw = self._load_json(concert_path)
            if isinstance(raw, list):
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    slug = (item.get("slug") or None)
                    href = (item.get("href") or None)
                    if not name:
                        continue
                    c = ConcertCity(name=name, slug=str(slug) if slug else None, href=str(href) if href else None)
                    # allow lookup by name and slug
                    self._concert_by_key[_norm_city_key(name)] = c
                    if c.slug:
                        self._concert_by_key[_norm_city_key(c.slug)] = c

        if os.path.exists(karabas_path):
            raw = self._load_json(karabas_path)
            if isinstance(raw, list):
                for item in raw:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    subdomain = (item.get("subdomain") or None)
                    url = (item.get("url") or None)
                    if not name:
                        continue
                    c = KarabasCity(
                        name=name,
                        subdomain=str(subdomain) if subdomain else None,
                        url=str(url) if url else None,
                    )
                    self._karabas_by_key[_norm_city_key(name)] = c
                    if c.subdomain:
                        self._karabas_by_key[_norm_city_key(c.subdomain)] = c

    def resolve_concert(self, city: str) -> ConcertCity | None:
        return self._concert_by_key.get(_norm_city_key(city))

    def resolve_karabas(self, city: str) -> KarabasCity | None:
        return self._karabas_by_key.get(_norm_city_key(city))


