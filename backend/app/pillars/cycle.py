"""Saeule 2 - Konjunktur (Denkschule Raoul Pal).

Der ISM-Index liegt nicht auf FRED. Ersatz: Durchschnitt der regionalen Fed-Industrieumfragen
Philadelphia, New York und Dallas. Alle drei sind Diffusionsindizes: Anteil der Firmen mit steigender
Aktivitaet minus Anteil mit fallender. 0 = keine Veraenderung, ueber 0 = Wachstum. Der Durchschnitt
laeuft historisch eng mit dem ISM.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timezone

from .. import fred
from ..fred import Observation, SeriesResult
from ..schemas import Component, Headline, PillarResponse, Point
from ..scoring import ScorePoint, score_history, score_series, tone_for
from ..services import compute_change, shift_dates
from ..model_config import CYCLE, PUBLICATION_LAG_DAYS
from .common import cached

NAME = "Konjunktur"
MEASURES = "Ob die US-Industrie gerade beschleunigt oder bremst."
LEGEND = "Raoul Pal"

REGIONS = {
    "phi": ("GACDFSA066MSFRBPHI", "Philadelphia"),
    "ny": ("GACDISA066MSFRBNY", "New York"),
    "dal": ("BACTSAMFRBDAL", "Dallas"),
}
# Ein Monat zaehlt erst, wenn genug Regionen gemeldet haben (die Umfragen erscheinen zeitversetzt).
MIN_REGIONS = 2


def compute_composite(series: Sequence[Sequence[Observation]], min_regions: int = MIN_REGIONS) -> list[Observation]:
    """Monatlicher Durchschnitt aller vorhandenen Regionen; Monate mit zu wenig Meldungen entfallen."""
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for observations in series:
        for o in observations:
            buckets[(o.date.year, o.date.month)].append(o.value)
    return [
        Observation(date=date(year, month, 1), value=sum(values) / len(values))
        for (year, month), values in sorted(buckets.items())
        if len(values) >= min_regions
    ]


def _component(cid: str, label: str, res: SeriesResult) -> Component:
    obs = res.observations
    ch = compute_change(obs, 13)
    return Component(
        id=cid,
        label=f"Fed {label}",
        value=obs[-1].value,
        unit="Punkte",
        format="diffusion",
        date=obs[-1].date,
        sign="+",
        change_13w_abs=ch.abs if ch else None,
        note=f"Monatliche Umfrage der Fed {label}: Anteil der Industriefirmen mit mehr Aktivität minus Anteil mit weniger.",
    )


async def _composite() -> tuple[list[Observation], list]:
    results = await asyncio.gather(*(fred.fetch_series(sid) for sid, _ in REGIONS.values()))
    composite = compute_composite([res.observations for res, _ in results])
    if not composite:
        raise fred.FredError("Konjunktur-Composite konnte nicht berechnet werden: zu wenig Daten.")
    return composite, results


async def history() -> list[ScorePoint]:
    """Im Verlauf zaehlt ein Monat erst ab Veroeffentlichung aller Umfragen (C3: kein Look-ahead von drei Wochen)."""
    composite, results = await _composite()
    key = tuple(res.fetched_at for res, _ in results)
    lagged = shift_dates(composite, PUBLICATION_LAG_DAYS["regional_fed"])
    return cached("cycle", key, lambda: score_history(lagged, **CYCLE.history_kwargs()))


async def build(history_len: int = 300) -> PillarResponse:
    composite, results = await _composite()

    breakdown = score_series([o.value for o in composite], **CYCLE.series_kwargs())
    latest = composite[-1]
    score = breakdown.score if breakdown else None
    fingerprint = hashlib.sha1(f"cycle:{latest.date}:{latest.value:.2f}:{score}".encode()).hexdigest()[:12]

    if breakdown:
        score_note = (
            f"Niveau: höher als in {breakdown.level} % der letzten 10 Jahre. "
            f"Momentum: 3-Monats-Trend im {breakdown.momentum}. Perzentil."
        )
    else:
        score_note = "Zu wenig Historie für einen Score."

    return PillarResponse(
        id="cycle",
        name=NAME,
        measures=MEASURES,
        legend=LEGEND,
        status="live",
        frequency="monthly",
        tone=tone_for(score),
        score=breakdown,
        score_note=score_note,
        headline=Headline(label="Regional-Fed-Composite (Industrie)", value=latest.value, unit="Punkte", format="diffusion", date=latest.date),
        change_13w=compute_change(composite, 13),
        change_52w=compute_change(composite, 52),
        components=[_component(cid, label, res) for (cid, (_, label)), (res, _) in zip(REGIONS.items(), results)],
        history=[Point(date=o.date, value=o.value) for o in composite[-history_len:]],
        source=results[0][0].source,
        fetched_at=datetime.fromtimestamp(max(res.fetched_at for res, _ in results), tz=timezone.utc),
        fingerprint=fingerprint,
    )
