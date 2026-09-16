"""Betrieb (Phase D): Refresh anstossen, Aenderungen und Tagesbilder lesen."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Header, HTTPException, Query

from .. import cboe, fred, market, shiller, store, treasury
from ..config import get_settings
from ..refresh import refresh

router = APIRouter(prefix="/api/v1", tags=["ops"])
DATA_ERRORS = (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError, treasury.TreasuryError)


@router.post("/refresh", summary="Quellen neu laden, Tagesbild speichern, Wechsel melden")
async def trigger_refresh(x_refresh_token: str | None = Header(default=None), force: bool = Query(True)) -> dict:
    token = get_settings().refresh_token
    if token and x_refresh_token != token:
        raise HTTPException(status_code=401, detail="Refresh-Token fehlt oder ist falsch.")
    try:
        return asdict(await refresh(force_network=force))
    except DATA_ERRORS as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/changes", summary="Erkannte Wechsel (Zone, Phase, Regime, Marktbestaetigung, Vetos)")
async def changes(days: int = Query(90, ge=1, le=3650), limit: int = Query(100, ge=1, le=500)) -> dict:
    return {"days": days, "events": store.list_events(days, limit), "last_refresh": store.get_meta("last_refresh"),
            "snapshot_date": store.get_meta("last_snapshot_date")}


@router.get("/snapshots", summary="Tagesbilder des Dashboards (Point-in-time)")
async def snapshots_list(days: int = Query(90, ge=1, le=3650)) -> dict:
    return {"days": days, "snapshots": store.list_snapshots(days)}
