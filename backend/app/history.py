"""Score-Zeitreihen aller Saeulen auf einem gemeinsamen Wochenraster plus Consensus-Verlauf.

Grundlage fuer die Score-Historie im Easy-Modus und fuer den Backtest. Jeder Punkt kennt nur
Daten bis zu seinem Datum (rollierende Perzentile in scoring.py).
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, datetime, timedelta, timezone

from .config import get_settings
from .consensus import DEFAULT_PARAMS, ConsensusParams, ConsensusState, CoreResult, Overlay, Snapshot, core, zone_for
from .model_config import CONSENSUS_WEIGHTS, PHASE_CONFIRM_WEEKS, RANK_MIN_HISTORY, RANK_WINDOW_WEEKS, ZONE_CONFIRM_WEEKS
from .scoring import RollingPercentile
from .pillars import cycle, liquidity, markets, mechanics, structure, valuation
from .pillars.common import forward_fill
from .scoring import ScorePoint
from .schemas import ConsensusHistoryPoint, HistoryPoint, HistoryResponse

HISTORY_PROVIDERS = {
    "liquidity": liquidity.history,
    "cycle": cycle.history,
    "markets": markets.history,
    "structure": structure.history,
    "mechanics": mechanics.history,
    "valuation": valuation.history,
}
# Wie alt ein Saeulen-Wert am Rastertag hoechstens sein darf (monatliche Daten brauchen mehr Spielraum).
MAX_AGE_DAYS = {"liquidity": 21, "cycle": 62, "markets": 21, "structure": 21, "mechanics": 21, "valuation": 75}

_cache: tuple[float, HistoryResponse] | None = None
_last_state: ConsensusState | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def weekly_grid(start: date, end: date) -> list[date]:
    """Jeden Sonntag von start bis end (ISO-Wochenende, alle Saeulen haben bis dahin gemeldet)."""
    first = start + timedelta(days=(6 - start.weekday()) % 7)
    out = []
    d = first
    while d <= end:
        out.append(d)
        d += timedelta(days=7)
    return out


async def aligned_pillars() -> tuple[list[date], dict[str, list[ScorePoint | None]]]:
    """Wochenraster und die darauf vorwaerts gefuellten Score-Punkte aller Saeulen."""
    settings = get_settings()
    names = list(HISTORY_PROVIDERS)
    histories = dict(zip(names, await asyncio.gather(*(HISTORY_PROVIDERS[n]() for n in names))))
    grid = weekly_grid(date(settings.history_start_year, 1, 1), date.today())
    return grid, {n: forward_fill(histories[n], grid, MAX_AGE_DAYS[n]) for n in names}


def composite_points(grid: list[date], aligned: dict[str, list[ScorePoint | None]],
                     params: ConsensusParams = DEFAULT_PARAMS) -> list[tuple[date, CoreResult]]:
    """Rohwert des Consensus je Woche, sobald alle Treiber (Schluessel der Gewichte) vorliegen. Overlays sind
    optional (kuerzere Historie); Regime-Naeherung: invertiertes Niveau im untersten Zehntel."""
    names = [n for n in params.weights if n in aligned]
    out: list[tuple[date, CoreResult]] = []
    for i, d in enumerate(grid):
        row = [aligned[n][i] for n in names]
        if any(p is None for p in row):
            continue
        drivers = dict(zip(names, (Snapshot(p.score, p.momentum, p.change) for p in row)))  # type: ignore[union-attr]
        val_p, mech_p = aligned["valuation"][i], aligned["mechanics"][i]
        valuation = Overlay(val_p.score, val_p.level <= 10) if val_p else None
        mechanics = Overlay(mech_p.score, mech_p.level <= 10) if mech_p else None
        out.append((d, core(drivers, valuation, mechanics, params)))
    return out


def rolling_rank(values: list[float], window: int = RANK_WINDOW_WEEKS, min_history: int = RANK_MIN_HISTORY) -> list[float | None]:
    """Perzentil jedes Werts gegenueber den vorherigen `window` Werten; None waehrend des Vorlaufs."""
    win = RollingPercentile(window)
    out: list[float | None] = []
    for i, v in enumerate(values):
        r = win.rank(v)
        out.append(r if i >= min_history and r is not None else None)
        win.push(v)
    return out


async def _compute() -> HistoryResponse:
    grid, aligned = await aligned_pillars()
    pillars = {
        n: [HistoryPoint(date=d, score=p.score, level=p.level, momentum=p.momentum) for d, p in zip(grid, pts) if p]
        for n, pts in aligned.items()
    }
    consensus: list[ConsensusHistoryPoint] = []
    confirmed: str | None = None
    candidate: str | None = None
    candidate_weeks = 0
    weeks_in_phase = 0
    composites: list[float] = []
    zone_conf: str | None = None
    zone_cand: str | None = None
    zone_cand_weeks = 0
    weeks_in_zone = 0
    points = composite_points(grid, aligned)
    ranks = rolling_rank([r.score for _, r in points])
    for (d, r), rank in zip(points, ranks):
        # Zyklusphase mit Hysterese: ein Wechsel gilt erst nach PHASE_CONFIRM_WEEKS Wochen in Folge.
        raw = r.phase_raw_key
        if confirmed is None:
            confirmed, weeks_in_phase = raw, 1
        elif raw == confirmed:
            weeks_in_phase += 1; candidate, candidate_weeks = None, 0
        else:
            if raw == candidate:
                candidate_weeks += 1
            else:
                candidate, candidate_weeks = raw, 1
            weeks_in_phase += 1
            if candidate_weeks >= PHASE_CONFIRM_WEEKS:
                confirmed, weeks_in_phase, candidate, candidate_weeks = raw, candidate_weeks, None, 0
        composites.append(r.score); composites = composites[-RANK_WINDOW_WEEKS:]
        if rank is None:
            continue
        zone_raw = zone_for(rank)[0]
        if zone_conf is None:
            zone_conf, weeks_in_zone = zone_raw, 1
        elif zone_raw == zone_conf:
            weeks_in_zone += 1; zone_cand, zone_cand_weeks = None, 0
        else:
            zone_cand_weeks = zone_cand_weeks + 1 if zone_raw == zone_cand else 1
            zone_cand = zone_raw
            weeks_in_zone += 1
            if zone_cand_weeks >= ZONE_CONFIRM_WEEKS:
                zone_conf, weeks_in_zone, zone_cand, zone_cand_weeks = zone_raw, zone_cand_weeks, None, 0
        consensus.append(ConsensusHistoryPoint(
            date=d, score=round(rank), composite=r.score, zone_key=zone_conf, zone_raw_key=zone_raw,  # type: ignore[arg-type]
            phase_key=confirmed, phase_raw_key=raw, liquidity_direction=r.liquidity_direction, growth_direction=r.growth_direction,  # type: ignore[arg-type]
        ))
    global _last_state
    _last_state = ConsensusState(
        window=list(composites), zone_key=zone_conf, weeks_in_zone=weeks_in_zone, phase_key=confirmed, weeks_in_phase=weeks_in_phase,
        zone_pending_key=zone_cand, zone_pending_weeks=zone_cand_weeks,
        last_date=consensus[-1].date if consensus else None,
    ) if confirmed and zone_conf else None
    return HistoryResponse(
        start=grid[0], end=grid[-1], pillars=pillars, consensus=consensus, generated_at=datetime.now(tz=timezone.utc)
    )


async def build_history(years: int | None = None) -> HistoryResponse:
    global _cache
    now = time.time()
    if _cache is None or now - _cache[0] >= get_settings().cache_ttl_seconds:
        _cache = (now, await _compute())
    resp = _cache[1]
    if not years:
        return resp
    cutoff = resp.end - timedelta(days=365 * years)
    return resp.model_copy(update={
        "start": max(resp.start, cutoff),
        "pillars": {n: [p for p in pts if p.date >= cutoff] for n, pts in resp.pillars.items()},
        "consensus": [p for p in resp.consensus if p.date >= cutoff],
    })


async def current_state() -> ConsensusState | None:
    """Rang-Fenster, bestaetigte Zone und Phase aus der Historie fuer den Live-Consensus."""
    await build_history()
    return _last_state
