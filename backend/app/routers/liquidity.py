"""Saeule 1 - Der Klempner (Michael Howell): Liquiditaet."""

from fastapi import APIRouter, HTTPException, Query

from .. import fred
from ..schemas import SeriesResponse
from ..services import SeriesMeta, build_series_response

router = APIRouter(prefix="/api/v1/liquidity", tags=["liquidity"])

WALCL: SeriesMeta = {
    "series_id": "WALCL",
    "title": "Fed-Bilanzsumme (Total Assets)",
    "unit": "Mio. USD",
    "frequency": "weekly",
}


@router.get("/fed-balance-sheet", response_model=SeriesResponse, summary="Fed-Bilanzsumme (WALCL)")
async def fed_balance_sheet(
    history: int = Query(52, ge=2, le=520, description="Anzahl Beobachtungen im Feld history"),
    refresh: bool = Query(False, description="Cache umgehen und FRED neu abfragen"),
) -> SeriesResponse:
    try:
        result, cached = await fred.fetch_series(WALCL["series_id"], force=refresh)
    except fred.FredError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return build_series_response(WALCL, result, cached=cached, history_len=history)
