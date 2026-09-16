"""FRED-Datenabruf.

Zwei Wege:
1. Offizielle FRED-API (empfohlen, braucht kostenlosen API-Key).
2. Fallback ohne Key: der oeffentliche CSV-Export `fredgraph.csv`. Liefert dieselben Daten,
   ist aber nicht offiziell dokumentiert - fuer Entwicklung okay, fuer Produktion den Key setzen.

Ergebnisse werden pro Serie im Speicher gecacht (TTL aus Settings), damit ein Dashboard-Reload
nicht jedes Mal FRED anfragt.
"""

from __future__ import annotations

import csv
import io
import ssl
import time
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

from . import store
from .config import get_settings

try:  # Nutzt den Zertifikatspeicher des Betriebssystems (auf Windows oft noetig).
    import truststore
except ImportError:  # pragma: no cover
    truststore = None

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

SOURCE_API = "fred-api"
SOURCE_CSV = "fred-csv"


class FredError(Exception):
    """FRED nicht erreichbar, Key ungueltig oder Antwort unbrauchbar."""


@dataclass(frozen=True)
class Observation:
    date: date
    value: float


@dataclass
class SeriesResult:
    series_id: str
    observations: list[Observation]  # aufsteigend nach Datum sortiert
    source: str
    fetched_at: float  # Unix-Timestamp


_cache: dict[str, SeriesResult] = {}


async def fetch_series(
    series_id: str, *, start: date | None = None, force: bool = False
) -> tuple[SeriesResult, bool]:
    """Holt eine FRED-Serie. Gibt (Ergebnis, aus_cache) zurueck."""
    settings = get_settings()
    now = time.time()

    cached = _cache.get(series_id)
    if cached and not force and now - cached.fetched_at < settings.cache_ttl_seconds:
        return cached, True
    # Platte (D1): frisch genug -> ohne Netz; sonst Netz, bei Ausfall Rueckfall auf die Platte.
    disk = store.load_raw("fred", series_id)
    if disk and not force and now - disk[1] < settings.disk_cache_ttl_seconds:
        _cache[series_id] = disk[0]
        return disk[0], True

    start = start or (date.today() - timedelta(weeks=settings.fred_history_weeks))
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=_ssl_verify()) as client:
            if settings.fred_api_key:
                observations = await _fetch_via_api(client, series_id, settings.fred_api_key, start)
                source = SOURCE_API
            else:
                observations = await _fetch_via_csv(client, series_id, start)
                source = SOURCE_CSV
        if not observations:
            raise FredError(f"FRED lieferte keine Beobachtungen fuer {series_id}.")
    except (FredError, httpx.HTTPError):
        if disk:
            _cache[series_id] = disk[0]
            return disk[0], True
        raise

    result = SeriesResult(series_id=series_id, observations=observations, source=source, fetched_at=now)
    _cache[series_id] = result
    store.save_raw("fred", series_id, result, now)
    return result, False


def clear_cache() -> None:
    _cache.clear()


def _ssl_verify() -> ssl.SSLContext | bool:
    if truststore is None:
        return True
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


async def _fetch_via_api(
    client: httpx.AsyncClient, series_id: str, api_key: str, start: date
) -> list[Observation]:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start.isoformat(),
        "sort_order": "asc",
    }
    try:
        response = await client.get(FRED_API_URL, params=params)
    except httpx.HTTPError as exc:
        raise FredError(f"FRED-API nicht erreichbar: {exc}") from exc

    if response.status_code != 200:
        raise FredError(f"FRED-API antwortete mit {response.status_code}: {_error_message(response)}")

    rows = ((o.get("date", ""), o.get("value", "")) for o in response.json().get("observations", []))
    return _parse_rows(rows)


async def _fetch_via_csv(client: httpx.AsyncClient, series_id: str, start: date) -> list[Observation]:
    try:
        response = await client.get(FRED_CSV_URL, params={"id": series_id})
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FredError(f"FRED-CSV-Export nicht erreichbar: {exc}") from exc

    reader = csv.reader(io.StringIO(response.text))
    header = next(reader, None)
    if not header or len(header) < 2:
        raise FredError("Unerwartetes CSV-Format von FRED.")

    rows = ((row[0], row[1]) for row in reader if len(row) >= 2)
    return [o for o in _parse_rows(rows) if o.date >= start]


def _parse_rows(rows: Iterable[tuple[str, str]]) -> list[Observation]:
    """Wandelt (datum, wert)-Paare in Observations um. FRED markiert fehlende Werte mit einem Punkt."""
    out: list[Observation] = []
    for raw_date, raw_value in rows:
        if raw_value in (".", "", None):
            continue
        try:
            out.append(Observation(date=date.fromisoformat(raw_date), value=float(raw_value)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda o: o.date)
    return out


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error_message", response.text[:200]))
    except ValueError:
        return response.text[:200]
