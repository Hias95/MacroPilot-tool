"""Fachlogik: aus rohen FRED-Beobachtungen Veraenderungen und API-Antworten ableiten."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict

from .fred import Observation, SeriesResult
from .schemas import Change, Point, SeriesResponse


class SeriesMeta(TypedDict):
    series_id: str
    title: str
    unit: str
    frequency: str


def compute_change(obs: Sequence[Observation], weeks: int) -> Change | None:
    """Veraenderung vom letzten Wert zum letzten Wert vor `weeks` Wochen. Datumsbasiert,
    funktioniert daher fuer woechentliche und taegliche Serien gleichermassen."""
    if not obs:
        return None
    latest = obs[-1]
    target = latest.date - timedelta(weeks=weeks)
    dates = [o.date for o in obs]
    i = bisect_right(dates, target) - 1
    if i < 0:
        return None
    base = obs[i]
    if base.value == 0:
        return None
    return Change(weeks=weeks, abs=latest.value - base.value, pct=(latest.value / base.value - 1.0) * 100.0)


def build_series_response(
    meta: SeriesMeta, result: SeriesResult, *, cached: bool, history_len: int
) -> SeriesResponse:
    obs = result.observations
    latest = obs[-1]
    previous = obs[-2] if len(obs) > 1 else None
    return SeriesResponse(
        series_id=meta["series_id"],
        title=meta["title"],
        unit=meta["unit"],
        frequency=meta["frequency"],
        latest=Point(date=latest.date, value=latest.value),
        previous=Point(date=previous.date, value=previous.value) if previous else None,
        change_1w=compute_change(obs, 1),
        change_13w=compute_change(obs, 13),
        change_52w=compute_change(obs, 52),
        history=[Point(date=o.date, value=o.value) for o in obs[-history_len:]],
        source=result.source,
        cached=cached,
        fetched_at=datetime.fromtimestamp(result.fetched_at, tz=timezone.utc),
    )


def resample_weekly(obs: Sequence[Observation]) -> list[Observation]:
    """Letzte Beobachtung je Kalenderwoche (taegliche Serien -> woechentlich)."""
    by_week: dict[tuple[int, int], Observation] = {}
    for o in obs:
        iso = o.date.isocalendar()
        by_week[(iso[0], iso[1])] = o
    return [by_week[k] for k in sorted(by_week)]


def year_over_year(obs: Sequence[Observation], periods: int = 12) -> list[Observation]:
    """Jahresrate in Prozent aus einer Indexreihe (periods Beobachtungen je Jahr).

    Die Basis ist die Beobachtung derselben Periode ein Jahr frueher, nicht die zwoelfte davor: fehlt ein Monat
    (etwa der CPI fuer Oktober 2025 nach dem Regierungsstillstand), verschiebt sich die Rechnung sonst um einen
    Monat. Perioden ohne Vorjahreswert entfallen."""
    if periods not in (12, 4):
        out: list[Observation] = []
        for i in range(periods, len(obs)):
            base = obs[i - periods].value
            if base:
                out.append(Observation(date=obs[i].date, value=(obs[i].value / base - 1.0) * 100.0))
        return out

    def key(d: date) -> tuple[int, int]:
        return (d.year, d.month) if periods == 12 else (d.year, (d.month - 1) // 3)

    by_key = {key(o.date): o.value for o in obs}
    out = []
    for o in obs:
        y, p = key(o.date)
        base = by_key.get((y - 1, p))
        if base:
            out.append(Observation(date=o.date, value=(o.value / base - 1.0) * 100.0))
    return out


def shift_dates(obs: Sequence[Observation], days: int) -> list[Observation]:
    """Verschiebt Termine um den Veroeffentlichungsverzug, damit die Historie nichts vorwegnimmt."""
    return [Observation(date=o.date + timedelta(days=days), value=o.value) for o in obs]


def ratio_series(numerator: Sequence[Observation], denominator: Sequence[Observation], scale: float = 100.0) -> list[Observation]:
    """Verhaeltnis zweier Reihen an gemeinsamen Terminen, standardmaessig in Prozent."""
    den = {o.date: o.value for o in denominator if o.value}
    return [Observation(date=o.date, value=o.value / den[o.date] * scale) for o in numerator if o.date in den]
