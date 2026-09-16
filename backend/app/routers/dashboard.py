"""Dashboard-Endpunkte: alle Saeulen plus Consensus, einzelne Saeule, KI-Erklaerung."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from .. import cboe, fred, market, shiller
from ..consensus import build_consensus
from ..easy import annotate
from ..explain import explain_pillar
from ..backtest import run_backtest
from ..data_quality import run_audit, to_dict
from ..history import build_history, current_state
from ..pillars import get_all, get_overlays, get_pillar
from ..schemas import DashboardResponse, ExplanationResponse, HistoryResponse, PillarId, PillarResponse

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse, summary="Alle Saeulen plus Consensus")
async def dashboard() -> DashboardResponse:
    try:
        pillars, overlays = await asyncio.gather(get_all(), get_overlays())
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        state = await current_state()
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError):
        state = None
    return DashboardResponse(
        consensus=build_consensus(pillars, overlays, state), pillars=[annotate(p) for p in pillars],
        overlays=[annotate(p) for p in overlays], generated_at=datetime.now(tz=timezone.utc),
    )


@router.get("/pillars/{pillar_id}", response_model=PillarResponse, summary="Eine Saeule")
async def pillar(pillar_id: PillarId) -> PillarResponse:
    try:
        return await get_pillar(pillar_id)
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/pillars/{pillar_id}/explanation", response_model=ExplanationResponse, summary="KI-Erklaerung zum Score")
async def explanation(pillar_id: PillarId) -> ExplanationResponse:
    try:
        p = await get_pillar(pillar_id)
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return await explain_pillar(p)


@router.get("/history", response_model=HistoryResponse, summary="Score-Verlauf aller Saeulen und des Consensus, woechentlich")
async def history(years: int | None = Query(None, ge=1, le=30, description="Nur die letzten N Jahre")) -> HistoryResponse:
    try:
        return await build_history(years)
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/backtest", summary="Backtest des Consensus gegen SPY (C1)")
async def backtest() -> dict:
    from dataclasses import asdict

    try:
        return asdict(await run_backtest())
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/data-quality", summary="Datenqualitaet: Luecken, Aktualitaet, Ausreisser, Rasterabdeckung (C3)")
async def data_quality() -> dict:
    try:
        return to_dict(await run_audit())
    except (fred.FredError, market.MarketError, cboe.CboeError, shiller.ShillerError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
