"""Overlay Marktsignale (Denkschule Stanley Druckenmiller): Bestaetigt der Markt das Makrobild?

Seit dem 16.09.2026 kein Treiber mehr (docs/marktsignale-rolle.md): das Niveau der Signale ist ein
Kontra-Signal, ihr Momentum kaum informativ. Der Score dient als Bestaetigung des Consensus (Divergenz-
Hinweis) und traegt das Regime-Flag Marktstress / Kapitulation.

Vier Signale, alle kostenlos als Wochenkurse ueber den Yahoo-Chart-Endpunkt:
  Breite          RSP / SPY     gleichgewichtet vs. kapitalgewichtet (seit 2003)
  Risikoappetit   AUD/JPY       Carry-Trade-Barometer, Rohstoffwaehrung gegen Fluchtwaehrung (seit 2003)
  Realwirtschaft  Kupfer / Gold Industriemetall gegen monetaeren Zufluchtsort, mal 1000 (seit 2001)
  Kredit          HYG / IEF     Hochzinsanleihen gegen Staatsanleihen; Proxy fuer den High-Yield-Spread,
                                dessen FRED-Historie auf drei Jahre begrenzt ist (seit 2007)
Jedes Signal bekommt einen eigenen Perzentil-plus-Momentum-Score, der Saeulen-Score ist ihr Mittel.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from .. import market
from ..fred import Observation
from ..model_config import MARKET_STRESS, MARKETS
from ..schemas import Component, Headline, PillarResponse, Point, RegimeCriterion, RegimeFlag, ScoreBreakdown
from ..scoring import ScorePoint, score_history, score_series, tone_for
from ..services import compute_change
from .common import average_points, cached

NAME = "Marktsignale"
MEASURES = "Ob der Markt das Makrobild bestätigt: Breite, Risikoappetit, Rohstoffe, Kredit."
LEGEND = "Stanley Druckenmiller"


@dataclass(frozen=True)
class Signal:
    id: str
    label: str
    numerator: str
    denominator: str | None
    note: str
    format: str = "ratio"
    unit: str = "Verhältnis"
    scale: float = 1.0


SIGNALS: list[Signal] = [
    Signal("breadth", "Breite: gleichgewichtet vs. Index", "RSP", "SPY",
           "Steigt, wenn die Masse der Aktien mitläuft statt nur weniger Riesen."),
    Signal("risk", "Risikoappetit: AUD/JPY", "AUDJPY=X", None,
           "Australischer Dollar gegen Yen. Steigt, wenn Anleger weltweit Risiko suchen; bricht ein, wenn Stress im Kreditsystem aufkommt.",
           format="price", unit="Yen"),
    Signal("real", "Realwirtschaft: Kupfer/Gold", "HG=F", "GC=F",
           "Kupfer braucht die Industrie, Gold ist der Zufluchtsort. Steigt das Verhältnis, preist der Markt Wachstum ein.",
           scale=1000.0, unit="Verhältnis ×1000"),
    Signal("credit", "Kredit: High Yield vs. Staatsanleihen", "HYG", "IEF",
           "Steigt, wenn Anleger riskanten Firmenanleihen vertrauen. Fällt oft als Erstes, wenn Stress aufkommt."),
]


def compute_ratio(
    numerator: Sequence[Observation], denominator: Sequence[Observation] | None, scale: float = 1.0
) -> list[Observation]:
    """Verhaeltnis zweier Kursreihen an gemeinsamen Terminen; ohne Nenner die Reihe selbst."""
    if denominator is None:
        return [Observation(date=o.date, value=o.value * scale) for o in numerator]
    den = {o.date: o.value for o in denominator if o.value}
    return [Observation(date=o.date, value=o.value / den[o.date] * scale) for o in numerator if o.date in den]


def aggregate(breakdowns: Sequence[ScoreBreakdown]) -> ScoreBreakdown:
    n = len(breakdowns)
    first = breakdowns[0]
    return ScoreBreakdown(
        score=round(sum(b.score for b in breakdowns) / n),
        level=round(sum(b.level for b in breakdowns) / n),
        momentum=round(sum(b.momentum for b in breakdowns) / n),
        level_weight=first.level_weight, momentum_window=first.momentum_window, lookback=first.lookback,
        unit=first.unit, method="mean-of-signal-scores",
    )


def stress_flag(score: int | None) -> RegimeFlag:
    """Marktstress unter stress_below, Kapitulation unter capitulation_below. Beides sind Stufen eines Flags."""
    stress, cap = MARKET_STRESS["stress_below"], MARKET_STRESS["capitulation_below"]
    s = score if score is not None else 50
    is_stress, is_cap = s < stress, s < cap
    return RegimeFlag(
        id="market_stress", label="Kapitulation" if is_cap else "Marktstress", active=is_stress,
        met_count=int(is_stress) + int(is_cap), needed=1,
        criteria=[
            RegimeCriterion(label=f"Marktsignal-Score unter {stress} (Stress)", value_text=f"{s}", met=is_stress),
            RegimeCriterion(label=f"Marktsignal-Score unter {cap} (Kapitulation)", value_text=f"{s}", met=is_cap),
        ],
        hint=("Der Ausverkauf ist weit fortgeschritten. Historisch folgten in 95 Prozent der Fälle positive Quartale, "
              "aber der Tiefpunkt lag oft noch einige Wochen voraus." if is_cap else
              "Das Geld zieht sich auf breiter Front zurück, Rückschläge verstärken sich. Historisch lag der Drawdown "
              "mit halber Aktienquote in solchen Phasen nur halb so tief."),
    )


async def _prices() -> dict[str, market.MarketResult]:
    tickers = sorted({t for s in SIGNALS for t in (s.numerator, s.denominator) if t})
    return await market.fetch_many(tickers)


def _series(prices: dict[str, market.MarketResult], s: Signal) -> list[Observation]:
    den = prices[s.denominator].observations if s.denominator else None
    return compute_ratio(prices[s.numerator].observations, den, s.scale)


async def history() -> list[ScorePoint]:
    """Mittel der vier Signal-Scores je Woche; Basis-Termine sind die der Breite (RSP/SPY)."""
    prices = await _prices()
    key = tuple(sorted((t, r.fetched_at) for t, r in prices.items()))

    def compute() -> list[ScorePoint]:
        histories = [score_history(_series(prices, s), **MARKETS.history_kwargs()) for s in SIGNALS]
        return average_points(histories[0], histories[1:], max_age_days=21)

    return cached("markets", key, compute)


async def build(history_len: int = 1300) -> PillarResponse:
    prices = await _prices()
    components: list[Component] = []
    breakdowns: list[ScoreBreakdown] = []
    series: dict[str, list[Observation]] = {}
    for s in SIGNALS:
        ratio = _series(prices, s)
        if len(ratio) < 30:
            raise market.MarketError(f"Zu wenig Kursdaten fuer {s.label}.")
        series[s.id] = ratio
        breakdown = score_series([o.value for o in ratio], **MARKETS.series_kwargs())
        if breakdown:
            breakdowns.append(breakdown)
        change = compute_change(ratio, 13)
        components.append(Component(
            id=s.id, label=s.label, value=ratio[-1].value, unit=s.unit, format=s.format,  # type: ignore[arg-type]
            date=ratio[-1].date, sign="+", change_13w_pct=round(change.pct, 3) if change else None,
            change_13w_abs=change.abs if change else None, score=breakdown.score if breakdown else None, note=s.note,
        ))

    total = aggregate(breakdowns) if breakdowns else None
    score = total.score if total else None
    breadth = series["breadth"]
    latest = breadth[-1]
    quote_date = max(r.latest_quote_date for r in prices.values())
    fingerprint = hashlib.sha1(f"markets:{latest.date}:{latest.value:.5f}:{score}".encode()).hexdigest()[:12]
    parts = ", ".join(f"{c.label.split(':')[0]} {c.score}" for c in components if c.score is not None)
    score_note = f"Mittel aus vier Signalen: {parts}. Kein Treiber, sondern Bestätigung des Consensus." if parts else "Zu wenig Historie für einen Score."

    return PillarResponse(
        id="markets", name=NAME, measures=MEASURES, legend=LEGEND, status="live", kind="overlay", frequency="weekly",
        tone=tone_for(score), score=total, score_note=score_note, regime=stress_flag(score),
        headline=Headline(label="Breite: RSP / SPY", value=latest.value, unit="Verhältnis", format="ratio", date=quote_date),
        change_1w=compute_change(breadth, 1), change_13w=compute_change(breadth, 13), change_52w=compute_change(breadth, 52),
        components=components,
        history=[Point(date=o.date, value=o.value) for o in breadth[-history_len:]],
        source=market.SOURCE,
        fetched_at=datetime.fromtimestamp(max(r.fetched_at for r in prices.values()), tz=timezone.utc),
        fingerprint=fingerprint,
    )
