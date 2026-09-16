"""CBOE-Indexhistorien (VIX, VIX3M) als CSV vom CBOE-CDN. Kostenlos, ohne Key, taeglich seit 1990 bzw. 2009."""

from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass
from datetime import datetime

import httpx

from . import store
from .config import get_settings
from .explain.base import ssl_context
from .fred import Observation

CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{name}_History.csv"
SOURCE = "cboe-csv"


class CboeError(Exception):
    """CBOE nicht erreichbar oder CSV unbrauchbar."""


@dataclass
class CboeResult:
    name: str
    observations: list[Observation]  # taeglich, Schlusskurse, aufsteigend
    source: str
    fetched_at: float


_cache: dict[str, CboeResult] = {}


def clear_cache() -> None:
    _cache.clear()


def parse_history(text: str) -> list[Observation]:
    """DATE,OPEN,HIGH,LOW,CLOSE mit Datum als MM/DD/YYYY."""
    reader = csv.DictReader(io.StringIO(text))
    out: list[Observation] = []
    for row in reader:
        try:
            d = datetime.strptime(row["DATE"].strip(), "%m/%d/%Y").date()
            out.append(Observation(date=d, value=float(row["CLOSE"])))
        except (KeyError, ValueError, AttributeError):
            continue
    out.sort(key=lambda o: o.date)
    return out


async def fetch_index(name: str, force: bool = False) -> tuple[CboeResult, bool]:
    now = time.time()
    settings = get_settings()
    cached = _cache.get(name)
    if cached and not force and now - cached.fetched_at < settings.cache_ttl_seconds:
        return cached, True
    disk = store.load_raw("cboe", name)
    if disk and not force and now - disk[1] < settings.disk_cache_ttl_seconds:
        _cache[name] = disk[0]
        return disk[0], True
    try:
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=ssl_context(), headers={"User-Agent": "Mozilla/5.0 (MacroPilot)"}) as client:
                response = await client.get(CBOE_URL.format(name=name))
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CboeError(f"CBOE nicht erreichbar ({name}): {exc}") from exc
        observations = parse_history(response.text)
        if not observations:
            raise CboeError(f"CBOE lieferte keine Daten fuer {name}.")
    except CboeError:
        if disk:
            _cache[name] = disk[0]
            return disk[0], True
        raise
    result = CboeResult(name=name, observations=observations, source=SOURCE, fetched_at=now)
    _cache[name] = result
    store.save_raw("cboe", name, result, now)
    return result, False
