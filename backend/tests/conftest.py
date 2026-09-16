"""Gemeinsame Fixtures: synthetische FRED- und Kursdaten, damit Tests offline und deterministisch laufen."""

import math
import os
import tempfile
import time
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

# Persistenz (D1) in ein Temp-Verzeichnis, Hintergrund-Refresh aus: Tests duerfen nie backend/data anfassen.
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="macropilot-test-"))
os.environ.setdefault("AUTO_REFRESH", "false")

from app import cboe, explain, fred, history, market, shiller, treasury  # noqa: E402
from app.fred import Observation, SeriesResult
from app.main import app
from app.pillars import common

GROWTH = {"^SKEW": 1.0001, "RSP": 1.0015, "SPY": 1.0020, "AUDJPY=X": 1.0008, "HG=F": 1.0012, "GC=F": 1.0018, "HYG": 1.0005, "IEF": 1.0002, "EURUSD=X": 1.0001, "JPY=X": 1.0003}


def synthetic(series_id: str) -> SeriesResult:
    start = date(2014, 9, 24)
    if series_id == "RRPONTSYD":
        obs = [Observation(date=start + timedelta(days=i), value=200 - i * 0.04) for i in range(620 * 7)]
    elif series_id in ("GACDFSA066MSFRBPHI", "GACDISA066MSFRBNY", "BACTSAMFRBDAL"):
        obs = [Observation(date=date(2014 + i // 12, 1 + i % 12, 1), value=10 * math.sin(i / 6) + 5) for i in range(150)]
    elif series_id in ("T10Y2Y", "DFII10"):
        obs = [Observation(date=start + timedelta(days=i), value=math.sin(i / 200) + (0.5 if series_id == "DFII10" else 0)) for i in range(620 * 7) if (start + timedelta(days=i)).weekday() < 5]
    elif series_id in ("TDSP", "A091RC1Q027SBEA", "W006RC1Q027SBEA"):
        base = {"TDSP": 10.0, "A091RC1Q027SBEA": 800.0, "W006RC1Q027SBEA": 3000.0}[series_id]
        obs = [Observation(date=date(2005 + i // 4, 1 + 3 * (i % 4), 1), value=base * (1 + 0.01 * i + 0.05 * math.sin(i / 5))) for i in range(86)]
    elif series_id in ("NCBEILQ027S", "GDP"):
        base = {"NCBEILQ027S": 20_000_000.0, "GDP": 15_000.0}[series_id]
        obs = [Observation(date=date(1995 + i // 4, 1 + 3 * (i % 4), 1), value=base * (1.012 ** i) * (1 + 0.15 * math.sin(i / 6))) for i in range(126)]
    elif series_id == "DGS10":
        obs = [Observation(date=start + timedelta(days=i), value=3.0 + math.sin(i / 300)) for i in range(620 * 7) if (start + timedelta(days=i)).weekday() < 5]
    elif series_id in ("CPILFESL", "CPIAUCSL"):
        obs = [Observation(date=date(2014 + i // 12, 1 + i % 12, 1), value=230 * (1.0025 + 0.001 * math.sin(i / 9)) ** i) for i in range(150)]
    elif series_id == "ECBASSETSW":
        obs = [Observation(date=start + timedelta(days=2) + timedelta(weeks=i), value=3_000_000 + i * 4_000) for i in range(620)]
    elif series_id == "JPNASSETS":
        obs = [Observation(date=date(2014 + i // 12, 1 + i % 12, 1), value=4_000_000 + i * 20_000) for i in range(150)]
    elif series_id == "WTREGEN":
        obs = [Observation(date=start + timedelta(weeks=i), value=400_000 + (i % 40) * 10_000) for i in range(620)]
    else:
        obs = [Observation(date=start + timedelta(weeks=i), value=4_000_000 + i * 5_000) for i in range(620)]
    return SeriesResult(series_id=series_id, observations=obs, source="fred-api", fetched_at=time.time())


def synthetic_prices(ticker: str) -> market.MarketResult:
    start = date(2011, 9, 12)
    obs = [Observation(date=start + timedelta(weeks=i), value=100 * GROWTH[ticker] ** i) for i in range(780)]
    return market.MarketResult(ticker=ticker, observations=obs, latest_quote_date=obs[-1].date, source="yahoo-chart", fetched_at=time.time())


@pytest.fixture
def client(monkeypatch):
    async def fake_fetch(series_id, *, start=None, force=False):
        return synthetic(series_id), False

    async def fake_prices(ticker, *, years=None, force=False):
        return synthetic_prices(ticker), False

    async def fake_cboe(name, force=False):
        start = date(2009, 9, 18) if name == "VIX3M" else date(2005, 1, 3)
        days = (date.today() - start).days
        obs = [Observation(date=start + timedelta(days=i), value=(20 if name == "VIX3M" else 18) + 6 * math.sin(i / 40)) for i in range(days) if (start + timedelta(days=i)).weekday() < 5]
        return cboe.CboeResult(name=name, observations=obs, source="cboe-csv", fetched_at=time.time()), False

    async def fake_shiller(force=False):
        n = (date.today().year - 1990) * 12 + date.today().month - 1
        cape = [Observation(date=date(1990 + i // 12, 1 + i % 12, 1), value=22 + 10 * math.sin(i / 50)) for i in range(n)]
        ecy = [Observation(date=o.date, value=100 / o.value - 1.5) for o in cape]
        return shiller.ShillerResult(cape=cape, ecy=ecy, source="shillerdata-xls", fetched_at=time.time()), False

    async def fake_tbill(force=False):
        today = date.today()
        months = (today.year - 2001) * 12 + today.month
        obs = [Observation(date=date(2001 + i // 12, 1 + i % 12, 28), value=20 + 3 * math.sin(i / 7)) for i in range(months)]
        return treasury.TreasuryResult(observations=obs, source="treasury-mspd", fetched_at=time.time()), False

    monkeypatch.setattr(fred, "fetch_series", fake_fetch)
    monkeypatch.setattr(market, "fetch_weekly_closes", fake_prices)
    monkeypatch.setattr(treasury, "fetch_tbill_share", fake_tbill)
    monkeypatch.setattr(cboe, "fetch_index", fake_cboe)
    monkeypatch.setattr(shiller, "fetch_shiller", fake_shiller)
    shiller.clear_cache()
    treasury.clear_cache()
    cboe.clear_cache()
    fred.clear_cache()
    market.clear_cache()
    explain.clear_cache()
    common.clear_caches()
    history.clear_cache()
    return TestClient(app)
