"""Score-Mathematik: Niveau (Perzentil-Rang) plus Momentum, beides 0 bis 100, ohne Blick in die Zukunft.

0 = maximal Risk-Off (Winter), 100 = maximal Risk-On (Sommer).
Perzentil-Raenge sind robust gegen Ausreisser und fuer Laien erklaerbar
("besser als in 80 % der letzten zehn Jahre"). Jeder Zeitpunkt sieht nur Daten davor.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right, insort
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal

from .fred import Observation
from .schemas import ScoreBreakdown, Tone

ChangeMode = Literal["pct", "abs"]


def percentile_rank(history: Sequence[float], current: float) -> float:
    """Anteil der historischen Werte unterhalb von current, in Prozent. Gleiche Werte zaehlen halb."""
    if not history:
        return 50.0
    below = sum(1 for v in history if v < current)
    equal = sum(1 for v in history if v == current)
    return 100.0 * (below + 0.5 * equal) / len(history)


class RollingPercentile:
    """Perzentil-Rang gegenueber einem gleitenden Fenster der zuletzt gesehenen Werte."""

    def __init__(self, window: int) -> None:
        self.window = max(1, window)
        self._sorted: list[float] = []
        self._queue: deque[float] = deque()

    def rank(self, value: float) -> float | None:
        n = len(self._sorted)
        if n == 0:
            return None
        lo = bisect_left(self._sorted, value)
        hi = bisect_right(self._sorted, value)
        return 100.0 * (lo + 0.5 * (hi - lo)) / n

    def push(self, value: float) -> None:
        insort(self._sorted, value)
        self._queue.append(value)
        if len(self._queue) > self.window:
            old = self._queue.popleft()
            del self._sorted[bisect_left(self._sorted, old)]


@dataclass(frozen=True)
class ScorePoint:
    date: date
    score: int
    level: int
    momentum: int
    change: float | None  # Veraenderung ueber das Momentum-Fenster (Prozent oder absolut, je nach Modus)


def _change(values: Sequence[float], i: int, window: int, mode: ChangeMode) -> float | None:
    if i < window:
        return None
    base = values[i - window]
    if mode == "abs":
        return values[i] - base
    if base == 0:
        return None
    return (values[i] / base - 1.0) * 100.0


def score_history_values(
    values: Sequence[float],
    *,
    momentum_window: int = 13,
    level_weight: float = 0.4,
    lookback: int = 520,
    min_history: int = 104,
    change_mode: ChangeMode = "pct",
) -> list[tuple[int, int, int, float | None]]:
    """(score, level, momentum, change) je Index ab min_history. Nur vorherige Werte fliessen ein."""
    level_win = RollingPercentile(lookback - 1)
    mom_win = RollingPercentile(max(1, lookback - momentum_window - 1))
    out: list[tuple[int, int, int, float | None]] = []
    for i, v in enumerate(values):
        change = _change(values, i, momentum_window, change_mode)
        if i >= min_history:
            level = level_win.rank(v)
            momentum = mom_win.rank(change) if change is not None else None
            if level is not None:
                m = 50.0 if momentum is None else momentum
                score = level_weight * level + (1.0 - level_weight) * m
                out.append((round(score), round(level), round(m), change))
            else:
                out.append((50, 50, 50, change))
        level_win.push(v)
        if change is not None:
            mom_win.push(change)
    return out


def score_history(
    observations: Sequence[Observation],
    *,
    momentum_window: int = 13,
    level_weight: float = 0.4,
    lookback: int = 520,
    min_history: int = 104,
    change_mode: ChangeMode = "pct",
) -> list[ScorePoint]:
    rows = score_history_values(
        [o.value for o in observations], momentum_window=momentum_window, level_weight=level_weight,
        lookback=lookback, min_history=min_history, change_mode=change_mode,
    )
    dates = [o.date for o in observations][min_history:]
    return [ScorePoint(d, s, lvl, m, ch) for d, (s, lvl, m, ch) in zip(dates, rows)]


def score_series(
    values: Sequence[float],
    *,
    momentum_window: int = 13,
    level_weight: float = 0.4,
    lookback: int = 520,
    unit: str = "weeks",
    change_mode: ChangeMode = "pct",
) -> ScoreBreakdown | None:
    """Score des letzten Werts einer Serie. Gleiche Rechnung wie score_history, nur der Endpunkt."""
    vals = list(values)
    if len(vals) < momentum_window + 8:
        return None
    rows = score_history_values(
        vals, momentum_window=momentum_window, level_weight=level_weight, lookback=lookback,
        min_history=len(vals) - 1, change_mode=change_mode,
    )
    score, level, momentum, change = rows[-1]
    return ScoreBreakdown(
        score=score, level=level, momentum=momentum, level_weight=level_weight,
        momentum_window=momentum_window, lookback=min(lookback, len(vals)), unit=unit,  # type: ignore[arg-type]
        method="percentile-level+momentum", change=change,
    )


def invert_point(p: ScorePoint) -> ScorePoint:
    return ScorePoint(p.date, 100 - p.score, 100 - p.level, 100 - p.momentum, None if p.change is None else -p.change)


def tone_for(score: int | None) -> Tone:
    if score is None:
        return "neutral"
    if score < 40:
        return "bearish"
    if score > 60:
        return "bullish"
    return "neutral"
