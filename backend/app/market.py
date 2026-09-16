"""Marktdaten (ETF-Kurse) ueber den Yahoo-Finance-Chart-Endpunkt, den auch yfinance intern nutzt.

Kostenlos, ohne Key. Liefert woechentliche, dividendenbereinigte Schlusskurse (adjclose), damit
Verhaeltnisse wie HYG/IEF nicht durch Ausschuettungen verzerrt werden. Ergebnisse werden pro Ticker
im Speicher gecacht (TTL wie FRED).
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx

from . import store
from .config import get_settings
from .explain.base import ssl_context
from .fred import Observation

YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
SOURCE = "yahoo-chart"
HEADERS = {"User-Agent": "Mozilla/5.0 (MacroPilot; +https://github.com)"}


class MarketError(Exception):
    """Yahoo nicht erreichbar oder Antwort unbrauchbar."""


@dataclass
class MarketResult:
    ticker: str
    observations: list[Observation]  # woechentlich, aufsteigend
    latest_quote_date: date  # letzter Handelstag laut Yahoo
    source: str
    fetched_at: float


_cache: dict[str, MarketResult] = {}


def clear_cache() -> None:
    _cache.clear()


async def fetch_weekly_closes(ticker: str, *, years: int | None = 25, force: bool = False) -> tuple[MarketResult, bool]:
    settings = get_settings()
    now = time.time()
    cached = _cache.get(ticker)
    if cached and not force and now - cached.fetched_at < settings.cache_ttl_seconds:
        return cached, True
    disk = store.load_raw("market", ticker)
    if disk and not force and now - disk[1] < settings.disk_cache_ttl_seconds:
        _cache[ticker] = disk[0]
        return disk[0], True
    try:
        async with httpx.AsyncClient(timeout=20.0, verify=ssl_context(), headers=HEADERS) as client:
            result = await _fetch(client, ticker, years, now)
    except (MarketError, httpx.HTTPError):
        if disk:
            _cache[ticker] = disk[0]
            return disk[0], True
        raise
    _cache[ticker] = result
    store.save_raw("market", ticker, result, now)
    return result, False


async def fetch_many(tickers: list[str]) -> dict[str, MarketResult]:
    results = await asyncio.gather(*(fetch_weekly_closes(t) for t in tickers))
    return {t: r for t, (r, _) in zip(tickers, results)}


async def _fetch(client: httpx.AsyncClient, ticker: str, years: int | None, now: float) -> MarketResult:
    # "max" liefert bei Yahoo nur Monatsbalken; eine feste Jahreszahl haelt die Wochenaufloesung.
    params = {"range": f"{years}y" if years else "max", "interval": "1wk", "includeAdjustedClose": "true"}
    try:
        response = await client.get(YAHOO_CHART_URL.format(ticker=ticker), params=params)
    except httpx.HTTPError as exc:
        raise MarketError(f"Yahoo Finance nicht erreichbar ({ticker}): {exc}") from exc
    if response.status_code != 200:
        raise MarketError(f"Yahoo Finance antwortete fuer {ticker} mit {response.status_code}.")
    try:
        result = response.json()["chart"]["result"][0]
        timestamps = result["timestamp"]
        indicators = result["indicators"]
        if indicators.get("adjclose"):
            closes = indicators["adjclose"][0]["adjclose"]
        else:  # Devisen und Futures haben keinen bereinigten Schlusskurs
            closes = indicators["quote"][0]["close"]
        quote_ts = result["meta"].get("regularMarketTime", timestamps[-1])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise MarketError(f"Unerwartete Yahoo-Antwort fuer {ticker}.") from exc

    observations = [
        Observation(date=datetime.fromtimestamp(ts, tz=timezone.utc).date(), value=float(value))
        for ts, value in zip(timestamps, closes)
        if value is not None
    ]
    observations.sort(key=lambda o: o.date)
    if not observations:
        raise MarketError(f"Keine Kurse fuer {ticker} erhalten.")
    return MarketResult(
        ticker=ticker,
        observations=observations,
        latest_quote_date=datetime.fromtimestamp(quote_ts, tz=timezone.utc).date(),
        source=SOURCE,
        fetched_at=now,
    )
