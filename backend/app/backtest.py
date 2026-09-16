"""Backtest C1: Wie gut sagt der Consensus kuenftige Aktienrenditen voraus?

Grundlage: die woechentliche Score-Historie (Sonntagsraster, kein Blick in die Zukunft) und SPY-Wochenkurse
(dividendenbereinigt). Fuer jede Woche gilt der Score vom Sonntag, die Rendite laeuft ab der Folgewoche.
Ausgewertet werden mehrere Varianten des Gesamtscores und jeder Baustein allein, damit die Kalibrierung
(C2) auf Zahlen steht. Cash verzinst sich mit dem 3-Monats-T-Bill (FRED WTB3MS).
"""

from __future__ import annotations

import math
import time
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import fred, market
from .history import build_history
from .model_config import CONSENSUS_WEIGHTS, ZONE_BANDS
from .scoring import RollingPercentile

HORIZONS = (4, 13, 26, 52)
# Zwei Aktienquoten-Profile je Zone: defensiv (0 bis 100 %) und Basis (50 bis 100 %, fuer Privatanleger realistischer).
EXPOSURE_DEFENSIVE = {"very_negative": 0.0, "negative": 0.25, "neutral": 0.5, "positive": 0.75, "very_positive": 1.0}
EXPOSURE_BASE = {"very_negative": 0.5, "negative": 0.7, "neutral": 0.85, "positive": 1.0, "very_positive": 1.0}


@dataclass
class BandStat:
    key: str
    label: str
    weeks: int
    share_pct: float
    mean_fwd_13w: float | None
    mean_fwd_52w: float | None
    hit_rate_13w: float | None


@dataclass
class StrategyStat:
    cagr_pct: float
    vol_pct: float
    sharpe: float
    max_drawdown_pct: float
    avg_exposure: float
    band_changes_per_year: float
    yearly: dict[int, float] = field(default_factory=dict)


@dataclass
class VariantResult:
    name: str
    weeks: int
    start: date
    end: date
    distribution: dict[str, float]
    ic: dict[int, float]
    bands: list[BandStat]
    deciles: list[tuple[int, float | None, float | None]]
    strategy: StrategyStat
    strategy_base: StrategyStat
    buy_hold: StrategyStat


def band_of(score: float) -> tuple[str, str]:
    for upper, key, label in ZONE_BANDS:
        if score < upper:
            return key, label
    return ZONE_BANDS[-1][1], ZONE_BANDS[-1][2]


def spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(v: list[float]) -> list[float]:
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for k in range(i, j + 1):
                r[order[k]] = (i + j) / 2 + 1
            i = j + 1
        return r
    if len(xs) < 3:
        return 0.0
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = math.sqrt(sum((a - mx) ** 2 for a in rx)); vy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return cov / (vx * vy) if vx and vy else 0.0


def percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return float("nan")
    pos = (len(sorted_vals) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


class PriceIndex:
    def __init__(self, observations):
        self.dates = [o.date for o in observations]
        self.values = [o.value for o in observations]

    def at(self, d: date) -> float | None:
        i = bisect_right(self.dates, d) - 1
        return self.values[i] if i >= 0 else None


def forward_return(prices: PriceIndex, d: date, weeks: int) -> float | None:
    """Rendite von d bis d + weeks; None, wenn der Zielkurs noch in der Zukunft liegt."""
    target = d + timedelta(weeks=weeks)
    if target > prices.dates[-1]:
        return None
    p0, p1 = prices.at(d), prices.at(target)
    if p0 is None or p1 is None:
        return None
    return p1 / p0 - 1.0


def _strategy(rows: list[tuple[date, float]], prices: PriceIndex, cash: PriceIndex, exposure_of) -> StrategyStat:
    value, peak, max_dd = 1.0, 1.0, 0.0
    weekly: list[float] = []
    excess: list[float] = []
    exposures: list[float] = []
    yearly: dict[int, float] = {}
    year_start: dict[int, float] = {}
    changes, prev_band = 0, None
    for i in range(len(rows) - 1):
        d, score = rows[i]
        band = band_of(score)[0]
        if prev_band is not None and band != prev_band:
            changes += 1
        prev_band = band
        e = exposure_of(score)
        p0, p1 = prices.at(d), prices.at(rows[i + 1][0])
        if p0 is None or p1 is None:
            continue
        r_eq = p1 / p0 - 1.0
        cash_rate = (cash.at(d) or 0.0) / 100.0 / 52.0
        r = e * r_eq + (1.0 - e) * cash_rate
        year_start.setdefault(d.year, value)
        value *= 1.0 + r
        yearly[d.year] = value / year_start[d.year] - 1.0
        peak = max(peak, value); max_dd = min(max_dd, value / peak - 1.0)
        weekly.append(r); excess.append(r - cash_rate); exposures.append(e)
    years = len(weekly) / 52.0
    cagr = value ** (1.0 / years) - 1.0 if years > 0 else 0.0
    mean_w = sum(weekly) / len(weekly) if weekly else 0.0
    vol = math.sqrt(sum((w - mean_w) ** 2 for w in weekly) / max(1, len(weekly) - 1)) * math.sqrt(52) if weekly else 0.0
    mean_ex = sum(excess) / len(excess) if excess else 0.0
    sharpe = (mean_ex * 52) / vol if vol else 0.0
    return StrategyStat(
        cagr_pct=round(cagr * 100, 2), vol_pct=round(vol * 100, 2), sharpe=round(sharpe, 2), max_drawdown_pct=round(max_dd * 100, 2),
        avg_exposure=round(sum(exposures) / len(exposures), 2) if exposures else 0.0,
        band_changes_per_year=round(changes / years, 1) if years else 0.0,
        yearly={y: round(v * 100, 1) for y, v in yearly.items()},
    )


def evaluate_series(name: str, points: list[tuple[date, float]], prices: PriceIndex, cash: PriceIndex) -> VariantResult:
    rows = [(d, float(s)) for d, s in points if prices.at(d) is not None]
    scores = sorted(s for _, s in rows)
    mean = sum(scores) / len(scores)
    distribution = {
        "min": round(scores[0], 1), "p10": round(percentile(scores, 0.1), 1), "p50": round(percentile(scores, 0.5), 1),
        "p90": round(percentile(scores, 0.9), 1), "max": round(scores[-1], 1),
        "std": round(math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores)), 1),
    }
    fwd = {h: [forward_return(prices, d, h) for d, _ in rows] for h in HORIZONS}
    ic = {}
    for h in HORIZONS:
        pairs = [(s, f) for (_, s), f in zip(rows, fwd[h]) if f is not None]
        ic[h] = round(spearman([a for a, _ in pairs], [b for _, b in pairs]), 3)

    bands: list[BandStat] = []
    for upper, key, label in ZONE_BANDS:
        idx = [i for i, (_, s) in enumerate(rows) if band_of(s)[0] == key]
        f13 = [fwd[13][i] for i in idx if fwd[13][i] is not None]
        f52 = [fwd[52][i] for i in idx if fwd[52][i] is not None]
        bands.append(BandStat(
            key=key, label=label, weeks=len(idx), share_pct=round(100 * len(idx) / len(rows), 1),
            mean_fwd_13w=round(100 * sum(f13) / len(f13), 2) if f13 else None,
            mean_fwd_52w=round(100 * sum(f52) / len(f52), 2) if f52 else None,
            hit_rate_13w=round(100 * sum(1 for f in f13 if f > 0) / len(f13), 1) if f13 else None,
        ))
    order = sorted(range(len(rows)), key=lambda i: rows[i][1])
    deciles = []
    for dec in range(10):
        chunk = order[dec * len(order) // 10:(dec + 1) * len(order) // 10]
        f13 = [fwd[13][i] for i in chunk if fwd[13][i] is not None]
        f52 = [fwd[52][i] for i in chunk if fwd[52][i] is not None]
        deciles.append((dec + 1, round(100 * sum(f13) / len(f13), 2) if f13 else None, round(100 * sum(f52) / len(f52), 2) if f52 else None))

    strategy = _strategy(rows, prices, cash, lambda s: EXPOSURE_DEFENSIVE[band_of(s)[0]])
    strategy_base = _strategy(rows, prices, cash, lambda s: EXPOSURE_BASE[band_of(s)[0]])
    buy_hold = _strategy(rows, prices, cash, lambda s: 1.0)
    return VariantResult(name=name, weeks=len(rows), start=rows[0][0], end=rows[-1][0], distribution=distribution,
                         ic=ic, bands=bands, deciles=deciles, strategy=strategy, strategy_base=strategy_base, buy_hold=buy_hold)


@dataclass
class BacktestReport:
    benchmark: str
    start: date
    end: date
    variants: list[VariantResult]
    generated_at: float


_cache: tuple[float, BacktestReport] | None = None


def clear_cache() -> None:
    global _cache
    _cache = None


def expanding_rank(rows: list[tuple[date, float]], min_history: int = 52) -> list[tuple[date, float]]:
    """Perzentil des Scores gegenueber allen frueheren Wochen (kein Blick in die Zukunft)."""
    win = RollingPercentile(10_000)
    out = []
    for i, (d, s) in enumerate(rows):
        if i >= min_history:
            out.append((d, win.rank(s) or 50.0))
        win.push(s)
    return out


def vote_score(driver_scores: dict[str, float], high: float = 60, low: float = 40) -> float:
    """Gewichtete Stimmen: +1 ab high, -1 bis low, sonst 0. Ergebnis auf 0 bis 100."""
    total = sum(CONSENSUS_WEIGHTS.values())
    v = sum(CONSENSUS_WEIGHTS[k] * (1 if s >= high else -1 if s <= low else 0) for k, s in driver_scores.items()) / total
    return 50 + 50 * v


async def run_backtest(force: bool = False) -> BacktestReport:
    global _cache
    now = time.time()
    if _cache and not force and now - _cache[0] < 3600:
        return _cache[1]
    history = await build_history()
    (spy, _), (tb, _) = await market.fetch_weekly_closes("SPY"), await fred.fetch_series("WTB3MS", start=date(2000, 1, 1))
    prices, cash = PriceIndex(spy.observations), PriceIndex(tb.observations)

    raw = [(p.date, float(p.composite)) for p in history.consensus]
    ranked = [(p.date, float(p.score)) for p in history.consensus]
    by_date = {k: {pt.date: float(pt.score) for pt in pts} for k, pts in history.pillars.items()}
    drivers = list(CONSENSUS_WEIGHTS)
    equal, votes = [], []
    for d, _ in raw:
        if all(d in by_date[k] for k in drivers):
            ds = {k: by_date[k][d] for k in drivers}
            equal.append((d, sum(ds.values()) / len(ds)))
            votes.append((d, vote_score(ds)))

    variants = [
        evaluate_series("Consensus Rang (10 Jahre rollierend, live)", ranked, prices, cash),
        evaluate_series("Consensus Rohwert", raw, prices, cash),
        evaluate_series("Stimmen-Modell (4 Treiber)", votes, prices, cash),
        evaluate_series("Ungewichtetes Mittel, ohne Overlays", equal, prices, cash),
    ]
    for k, pts in history.pillars.items():
        variants.append(evaluate_series(f"Nur {k}", [(pt.date, float(pt.score)) for pt in pts], prices, cash))
    report = BacktestReport(benchmark="SPY", start=raw[0][0], end=raw[-1][0], variants=variants, generated_at=now)
    _cache = (now, report)
    return report


def format_report(report: BacktestReport) -> str:
    lines = [f"Backtest gegen {report.benchmark}, {report.start} bis {report.end}", ""]
    for v in report.variants:
        s, b = v.strategy, v.buy_hold
        lines.append(f"== {v.name} ({v.weeks} Wochen, {v.start} bis {v.end})")
        d = v.distribution
        lines.append(f"   Verteilung: min {d['min']} | p10 {d['p10']} | median {d['p50']} | p90 {d['p90']} | max {d['max']} | std {d['std']}")
        lines.append("   Rangkorrelation Score vs. Vorwaertsrendite: " + ", ".join(f"{h}W {v.ic[h]:+.3f}" for h in HORIZONS))
        lines.append("   Zonen: " + " | ".join(f"{bs.label} {bs.share_pct}% (13W {bs.mean_fwd_13w}%, Treffer {bs.hit_rate_13w}%, 52W {bs.mean_fwd_52w}%)" for bs in v.bands))
        lines.append("   Dezile 13W: " + " ".join(f"D{dec}:{f13}" for dec, f13, _ in v.deciles))
        lines.append(f"   Strategie defensiv: CAGR {s.cagr_pct}% | Vol {s.vol_pct}% | Sharpe {s.sharpe} | MaxDD {s.max_drawdown_pct}% | Exposure {s.avg_exposure} | Zonenwechsel/Jahr {s.band_changes_per_year}")
        sb = v.strategy_base
        lines.append(f"   Strategie Basis:    CAGR {sb.cagr_pct}% | Vol {sb.vol_pct}% | Sharpe {sb.sharpe} | MaxDD {sb.max_drawdown_pct}% | Exposure {sb.avg_exposure}")
        lines.append(f"   Buy&Hold:  CAGR {b.cagr_pct}% | Vol {b.vol_pct}% | Sharpe {b.sharpe} | MaxDD {b.max_drawdown_pct}%")
        lines.append("   Jahre (Strategie/B&H): " + " ".join(f"{y}:{s.yearly[y]}/{b.yearly.get(y)}" for y in sorted(s.yearly) if y in (2009, 2011, 2015, 2018, 2020, 2022, 2023, 2024, 2025)))
        lines.append("")
    return "\n".join(lines)
