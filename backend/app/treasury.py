"""US-Treasury Fiscal Data API: Anteil der T-Bills an den marktfaehigen Staatsschulden, monatlich.

Kostenlos, ohne Key. Quelle: Monthly Statement of the Public Debt (MSPD), Tabelle 1.
Ein hoher Anteil (ueber 20 %) heisst: Der Staat finanziert sich kurzfristig, was Geldmarktfonds aus
der Reverse-Repo-Fazilitaet zieht und Liquiditaet in den Markt spuelt (Napier, Pozsar, Alden).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

import httpx

from . import store
from .config import get_settings
from .explain.base import ssl_context
from .fred import Observation

MSPD_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/debt/mspd/mspd_table_1"
SOURCE = "treasury-mspd"


class TreasuryError(Exception):
    """Fiscal-Data-API nicht erreichbar oder Antwort unbrauchbar."""


@dataclass
class TreasuryResult:
    observations: list[Observation]  # T-Bill-Anteil in Prozent, monatlich, aufsteigend
    source: str
    fetched_at: float


_cache: TreasuryResult | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def parse_tbill_share(rows: list[dict]) -> list[Observation]:
    """Bills / Total Marketable je record_date, in Prozent."""
    bills: dict[str, float] = {}
    totals: dict[str, float] = {}
    for row in rows:
        try:
            amount = float(row["debt_held_public_mil_amt"])
        except (KeyError, TypeError, ValueError):
            continue
        if row.get("security_type_desc") == "Marketable" and row.get("security_class_desc") == "Bills":
            bills[row["record_date"]] = amount
        elif row.get("security_type_desc") == "Total Marketable":
            totals[row["record_date"]] = amount
    out = [
        Observation(date=date.fromisoformat(d), value=bills[d] / totals[d] * 100.0)
        for d in bills if d in totals and totals[d]
    ]
    out.sort(key=lambda o: o.date)
    return out


async def fetch_tbill_share(force: bool = False) -> tuple[TreasuryResult, bool]:
    global _cache
    now = time.time()
    settings = get_settings()
    if _cache and not force and now - _cache.fetched_at < settings.cache_ttl_seconds:
        return _cache, True
    disk = store.load_raw("treasury", "tbill_share")
    if disk and not force and now - disk[1] < settings.disk_cache_ttl_seconds:
        _cache = disk[0]
        return _cache, True
    params = {
        "filter": "security_class_desc:in:(Bills,_)",
        "fields": "record_date,security_type_desc,security_class_desc,debt_held_public_mil_amt",
        "sort": "-record_date",
        "page[size]": "2000",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=ssl_context()) as client:
            response = await client.get(MSPD_URL, params=params)
            response.raise_for_status()
            rows = response.json().get("data", [])
    except (httpx.HTTPError, ValueError) as exc:
        if disk:
            _cache = disk[0]
            return _cache, True
        raise TreasuryError(f"Treasury Fiscal Data nicht erreichbar: {exc}") from exc
    observations = parse_tbill_share(rows)
    if not observations:
        if disk:
            _cache = disk[0]
            return _cache, True
        raise TreasuryError("Treasury Fiscal Data lieferte keine T-Bill-Daten.")
    _cache = TreasuryResult(observations=observations, source=SOURCE, fetched_at=now)
    store.save_raw("treasury", "tbill_share", _cache, now)
    return _cache, False
