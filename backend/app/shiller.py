"""Robert Shillers Datensatz (CAPE, Excess CAPE Yield), monatlich seit 1881.

Quelle: shillerdata.com verlinkt die aktuelle ie_data.xls auf einem CDN mit wechselnder Versionsnummer,
deshalb wird der Link bei jedem Abruf von der Seite gelesen. Fallback: die Yale-Datei (endet 2023).
Datumsformat in der Datei: JJJJ.MM als Zahl, wobei Oktober als JJJJ.1 erscheint.
"""

from __future__ import annotations

import io
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import httpx
import xlrd

from . import store
from .config import get_settings
from .explain.base import ssl_context
from .fred import Observation

PAGE_URL = "https://shillerdata.com/"
LINK_PATTERN = re.compile(r'(//img1\.wsimg\.com/blobby/[^"\']*?ie_data\.xls[^"\']*)')
FALLBACK_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
CACHE_SECONDS = 24 * 3600
SOURCE_CURRENT = "shillerdata-xls"
SOURCE_FALLBACK = "yale-xls-stale"


class ShillerError(Exception):
    """Shiller-Daten nicht erreichbar oder unbrauchbar."""


@dataclass
class ShillerResult:
    cape: list[Observation]  # monatlich, aufsteigend
    ecy: list[Observation]   # Excess CAPE Yield in Prozent
    source: str
    fetched_at: float


_cache: ShillerResult | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def shiller_date(value: float) -> date:
    year = int(value)
    month = int(round((value - year) * 100))
    return date(year, max(1, min(12, month)), 1)


def parse_rows(rows: Sequence[Sequence[object]]) -> tuple[list[Observation], list[Observation]]:
    """Findet CAPE- und Excess-CAPE-Yield-Spalte ueber die mehrzeilige Kopfzeile und liest die Daten."""
    header_rows = [r for r in rows[:10]]
    ncols = max(len(r) for r in header_rows)
    headers = [" ".join(str(r[j]).strip() for r in header_rows if j < len(r) and str(r[j]).strip()) for j in range(ncols)]
    cape_col = next((j for j, h in enumerate(headers) if "P/E10" in h and "TR" not in h), None)
    ecy_col = next((j for j, h in enumerate(headers) if "Excess" in h and "Yield" in h), None)
    if cape_col is None or ecy_col is None:
        raise ShillerError("CAPE- oder Excess-CAPE-Yield-Spalte nicht gefunden.")
    cape: list[Observation] = []
    ecy: list[Observation] = []
    for r in rows:
        if not r or not isinstance(r[0], (int, float)) or r[0] < 1800:
            continue
        d = shiller_date(float(r[0]))
        c = r[cape_col] if cape_col < len(r) else None
        e = r[ecy_col] if ecy_col < len(r) else None
        if isinstance(c, (int, float)) and c:
            cape.append(Observation(date=d, value=float(c)))
        if isinstance(e, (int, float)) and e != "":
            ecy.append(Observation(date=d, value=float(e) * 100.0))
    if not cape:
        raise ShillerError("Keine CAPE-Daten in der Datei.")
    return cape, ecy


def parse_workbook(content: bytes) -> tuple[list[Observation], list[Observation]]:
    book = xlrd.open_workbook(file_contents=content)
    sheet = book.sheet_by_name("Data")
    return parse_rows([sheet.row_values(i) for i in range(sheet.nrows)])


async def fetch_shiller(force: bool = False) -> tuple[ShillerResult, bool]:
    global _cache
    now = time.time()
    if _cache and not force and now - _cache.fetched_at < CACHE_SECONDS:
        return _cache, True
    disk = store.load_raw("shiller", "ie_data")
    if disk and not force and now - disk[1] < get_settings().disk_cache_ttl_seconds:
        _cache = disk[0]
        return _cache, True
    headers = {"User-Agent": "Mozilla/5.0 (MacroPilot)"}
    source = SOURCE_CURRENT
    try:
        try:
            async with httpx.AsyncClient(timeout=120.0, verify=ssl_context(), follow_redirects=True, headers=headers) as client:
                try:
                    page = await client.get(PAGE_URL)
                    match = LINK_PATTERN.search(page.text)
                    if not match:
                        raise ShillerError("Kein ie_data.xls-Link auf shillerdata.com gefunden.")
                    response = await client.get("https:" + match.group(1))
                    response.raise_for_status()
                except (httpx.HTTPError, ShillerError):
                    source = SOURCE_FALLBACK
                    response = await client.get(FALLBACK_URL)
                    response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ShillerError(f"Shiller-Daten nicht erreichbar: {exc}") from exc
        cape, ecy = parse_workbook(response.content)
    except ShillerError:
        if disk:
            _cache = disk[0]
            return _cache, True
        raise
    _cache = ShillerResult(cape=cape, ecy=ecy, source=source, fetched_at=now)
    store.save_raw("shiller", "ie_data", _cache, now)
    return _cache, False
