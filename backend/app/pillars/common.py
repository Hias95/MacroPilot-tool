"""Gemeinsame Helfer fuer Score-Zeitreihen: Cache je Datenstand, Vorwaertsfuellen, Mittelung."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable, Sequence
from datetime import date
from typing import TypeVar

from ..schemas import ScoreBreakdown
from ..scoring import ScorePoint

T = TypeVar("T")
_caches: dict[str, tuple[tuple, object]] = {}


def cached(name: str, key: tuple, compute: Callable[[], T]) -> T:
    """Berechnet compute() nur, wenn sich der Datenstand (key) geaendert hat."""
    hit = _caches.get(name)
    if hit and hit[0] == key:
        return hit[1]  # type: ignore[return-value]
    value = compute()
    _caches[name] = (key, value)
    return value


def clear_caches() -> None:
    _caches.clear()


def forward_fill(points: Sequence[ScorePoint], targets: Sequence[date], max_age_days: int) -> list[ScorePoint | None]:
    """Fuer jedes Zieldatum der letzte Punkt davor, sofern nicht aelter als max_age_days."""
    dates = [p.date for p in points]
    out: list[ScorePoint | None] = []
    for target in targets:
        i = bisect_right(dates, target) - 1
        if i < 0 or (target - dates[i]).days > max_age_days:
            out.append(None)
        else:
            out.append(points[i])
    return out


def average_points(
    base: Sequence[ScorePoint],
    others: Sequence[Sequence[ScorePoint]],
    *,
    max_age_days: int | Sequence[int] = 21,
    weights: Sequence[float] | None = None,
) -> list[ScorePoint]:
    """Gewichtetes Mittel von Score, Niveau und Momentum mehrerer Serien auf den Terminen der Basis.
    Termine, an denen eine Serie fehlt, entfallen. Die Veraenderung stammt von der Basis-Serie.
    max_age_days gilt je Serie (Liste) oder fuer alle; weights beginnt mit der Basis."""
    targets = [p.date for p in base]
    ages = list(max_age_days) if not isinstance(max_age_days, int) else [max_age_days] * len(others)
    filled = [forward_fill(o, targets, age) for o, age in zip(others, ages)]
    w = list(weights) if weights else [1.0] * (1 + len(others))
    total = sum(w)
    out: list[ScorePoint] = []
    for i, b in enumerate(base):
        row = [b] + [f[i] for f in filled]
        if any(p is None for p in row):
            continue
        out.append(ScorePoint(
            date=b.date,
            score=round(sum(wi * p.score for wi, p in zip(w, row)) / total),  # type: ignore[union-attr]
            level=round(sum(wi * p.level for wi, p in zip(w, row)) / total),  # type: ignore[union-attr]
            momentum=round(sum(wi * p.momentum for wi, p in zip(w, row)) / total),  # type: ignore[union-attr]
            change=b.change,
        ))
    return out


def weighted_breakdown(parts: dict[str, ScoreBreakdown], weights: dict[str, float], method: str) -> ScoreBreakdown:
    """Gewichtetes Mittel mehrerer Teil-Scores; fehlende Teile werden herausgewichtet."""
    w = {k: weights[k] for k in parts}
    total = sum(w.values())
    first = next(iter(parts.values()))  # Basis-Serie: liefert Fenster und Veraenderung, wie average_points im Verlauf
    return ScoreBreakdown(
        score=round(sum(w[k] * b.score for k, b in parts.items()) / total),
        level=round(sum(w[k] * b.level for k, b in parts.items()) / total),
        momentum=round(sum(w[k] * b.momentum for k, b in parts.items()) / total),
        level_weight=first.level_weight, momentum_window=first.momentum_window, lookback=first.lookback, unit=first.unit,
        method=method, change=first.change,
    )
