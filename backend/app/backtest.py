"""Backtest C1: Wie gut sagt der Consensus kuenftige Aktienrenditen voraus?

Grundlage: die woechentliche Score-Historie (Sonntagsraster, kein Blick in die Zukunft) und SPY-Wochenkurse
(dividendenbereinigt). Fuer jede Woche gilt der Score vom Sonntag, die Rendite laeuft ab der Folgewoche.
Ausgewertet werden mehrere Varianten des Gesamtscores und jeder Baustein allein, damit die Kalibrierung
(C2) auf Zahlen steht. Cash verzinst sich mit dem 3-Monats-T-Bill (FRED WTB3MS).
"""

from __future__ import annotations

import logging
import math
import time
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import fred, market
from .consensus import market_confirmation
from .history import build_history
from .model_config import CONSENSUS_WEIGHTS, ZONE_BANDS
from .pillars.valuation import fallhoehe_label
from .scoring import RollingPercentile

log = logging.getLogger(__name__)

HORIZONS = (4, 13, 26, 52)
# Zwei Aktienquoten-Profile je Zone: defensiv (0 bis 100 %) und Basis (50 bis 100 %, fuer Privatanleger realistischer).
EXPOSURE_DEFENSIVE = {"very_negative": 0.0, "negative": 0.25, "neutral": 0.5, "positive": 0.75, "very_positive": 1.0}
EXPOSURE_BASE = {"very_negative": 0.5, "negative": 0.7, "neutral": 0.85, "positive": 1.0, "very_positive": 1.0}


def _quantile(values: list[float], q: float) -> float | None:
    """Perzentil einer Renditeliste in Prozent, lineare Interpolation. Leere Liste ergibt None."""
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return round(100 * xs[0], 2)
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    val = xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
    return round(100 * val, 2)


def effective_n(n_weeks: int, episodes: int, horizon: int = 13) -> int:
    """Zahl der praktisch unabhaengigen Beobachtungen.

    Woechentliche Fenster ueber 13 Wochen ueberlappen sich um zwoelf Dreizehntel, 315 Wochen sind also eher
    24 unabhaengige Faelle. Zugleich liegen viele Wochen im selben Zonenaufenthalt. Genommen wird der
    kleinere der beiden Werte, weil beide Effekte gleichzeitig wirken.
    """
    return max(1, min(episodes if episodes > 0 else n_weeks, n_weeks // horizon if n_weeks >= horizon else 1))


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95-Prozent-Intervall einer Trefferquote nach Wilson, in Prozent.

    Die Normalnaeherung ergaebe bei einer Quote von 100 Prozent eine Spanne von null und wuerde damit genau
    dort Sicherheit vortaeuschen, wo die Stichprobe am duennsten ist. Wilson tut das nicht.
    """
    if n <= 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * max(0.0, centre - half), 1), round(100 * min(1.0, centre + half), 1)


def _episodes(indices: list[int]) -> int:
    """Zusammenhaengende Aufenthalte in einer Zone. Zwei benachbarte Wochen zaehlen als eine Episode."""
    if not indices:
        return 0
    return 1 + sum(1 for a, b in zip(indices, indices[1:]) if b != a + 1)


def _uncertainty(f13: list[float], episodes: int) -> dict:
    """Effektive Stichprobe und Wilson-Intervall als Felder fuer BandStat."""
    if not f13:
        return {"n_effective": 0, "hit_low_13w": None, "hit_high_13w": None}
    n_eff = effective_n(len(f13), episodes)
    hits = round(sum(1 for f in f13 if f > 0) / len(f13) * n_eff)
    lo_hi = wilson_interval(hits, n_eff)
    return {"n_effective": n_eff, "hit_low_13w": lo_hi[0] if lo_hi else None, "hit_high_13w": lo_hi[1] if lo_hi else None}


@dataclass
class BandStat:
    key: str
    label: str
    weeks: int
    share_pct: float
    mean_fwd_13w: float | None
    mean_fwd_52w: float | None
    hit_rate_13w: float | None
    # Spannweite statt nur Mittelwert: p10 ist das schlechteste Zehntel, p90 das beste.
    p10_fwd_13w: float | None = None
    p50_fwd_13w: float | None = None
    p90_fwd_13w: float | None = None
    # Wochen ueberlappen sich stark. `episodes` zaehlt zusammenhaengende Aufenthalte in der Zone und ist das
    # ehrlichere Mass fuer die Belastbarkeit: 53 Wochen koennen fuenf Episoden sein.
    episodes: int = 0
    n_13w: int = 0
    #: Praktisch unabhaengige Faelle und das daraus folgende 95-Prozent-Intervall der Trefferquote.
    n_effective: int = 0
    hit_low_13w: float | None = None
    hit_high_13w: float | None = None


# C1: Der Consensus misst das Umfeld fuer US-Aktien. Ob er auch ueber Gold und Anleihen etwas sagt, war
# bisher unbelegt, obwohl das Regime-Flag "Fiskalische Dominanz" genau das behauptet. Alles investierbare
# ETFs, damit die Zahlen vergleichbar bleiben.
BENCHMARK_TICKERS = [("SPY", "S&P 500"), ("GLD", "Gold"), ("IEF", "US-Staatsanleihen 7 bis 10 J")]
MIXED_NAME = "Mischung 60 Aktien / 40 Anleihen"
# C2: Die Gewichte wurden auf Daten bis Ende 2018 kalibriert. Alles danach ist echtes Pruef-Fenster.
TEST_WINDOW_START = date(2019, 1, 1)


@dataclass
class BenchmarkBand:
    zone: str
    n_13w: int
    episodes: int
    hit_rate_13w: float | None
    median_13w: float | None


@dataclass
class BenchmarkResult:
    """Wie sich eine Anlage nach Wochen in jeder Zone entwickelt hat. Gleiche Rechnung wie beim Hauptindex."""

    key: str
    name: str
    start: date
    bands: list[BenchmarkBand]
    #: Rangkorrelation Score gegen Vorwaertsertrag. Sagt, ob die Zonen ueberhaupt unterschieden haben.
    #: Trefferquoten je Zone taugen dafuer nicht: In einem steigenden Markt sind sie ueberall hoch, auch
    #: wenn die Reihenfolge der Zonen gar nicht stimmt.
    ic_13w: float | None = None
    weeks: int = 0


@dataclass
class ConditionalBand:
    """Vorwaertsrendite einer Zone unter einer zusaetzlichen Bedingung.

    Die unbedingte Aussage ("nach neutralen Wochen ging es meist hoch") laesst offen, ob das auch galt, als der
    Markt gleichzeitig extrem teuer war. Genau das ist die Frage, die ein Leser mit Erfahrung zuerst stellt.
    """

    zone: str
    condition: str
    label: str
    weeks: int
    episodes: int
    n_13w: int
    hit_rate_13w: float | None
    mean_fwd_13w: float | None
    p10_fwd_13w: float | None
    p50_fwd_13w: float | None


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
            p10_fwd_13w=_quantile(f13, 0.10), p50_fwd_13w=_quantile(f13, 0.50), p90_fwd_13w=_quantile(f13, 0.90),
            episodes=_episodes(idx), n_13w=len(f13),
            **_uncertainty(f13, _episodes(idx)),
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
    conditional: list[ConditionalBand] = field(default_factory=list)
    benchmarks: list[BenchmarkResult] = field(default_factory=list)
    #: Dieselbe Rechnung nur auf dem Pruef-Fenster, also ausserhalb der Kalibrierung.
    test_window: BenchmarkResult | None = None
    #: Und dieselbe Rechnung davor. Die Untersuchung vom 18.09.2026 zeigte, dass die Prognosekraft des
    #: Modells fast ganz aus den spaeteren Jahren stammt; das gehoert sichtbar daneben.
    early_window: BenchmarkResult | None = None
    generated_at: float = 0.0


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


# Zusatzbedingungen, unter denen dieselbe Zone sehr verschieden ausgehen kann. Die Schwellen sind dieselben
# wie in der Oberflaeche (VALUATION_LABELS, MARKET_CONFIRM_THRESHOLD), damit "extrem teuer" hier und dort
# dasselbe heisst.
CONDITION_LABELS = {
    "valuation_extreme": "bei extrem teurem Markt",
    "valuation_other": "wenn der Markt nicht extrem teuer war",
    "market_confirmed": "wenn der Markt das Bild bestätigte",
    "market_other": "wenn der Markt das Bild nicht bestätigte",
}


def conditional_bands(rows: list[tuple[date, float]], fwd13: list[float | None],
                      valuation: dict[date, float], markets: dict[date, float]) -> list[ConditionalBand]:
    """Je Zone und Zusatzbedingung dieselben Kennzahlen wie in den Zonen-Baendern.

    Zur Zaehlung der Episoden: Eine Bedingung springt innerhalb desselben Zonenaufenthalts hin und her, etwa
    wenn der Markt in einer neutralen Phase mal bestaetigt und mal nicht. Zusammenhaengende Abschnitte der
    Teilmenge zu zaehlen ergaebe dann mehr "Episoden" als die Zone insgesamt hat, was Unabhaengigkeit
    vortaeuschen wuerde. Gezaehlt wird deshalb, wie viele **Zonenaufenthalte** ueberhaupt betroffen sind.
    """
    # Zonenaufenthalte durchnummerieren: aufeinanderfolgende Wochen derselben Zone gehoeren zusammen.
    stay_of: list[int] = []
    prev_zone, stay = None, -1
    for _, score in rows:
        zone = band_of(score)[0]
        if zone != prev_zone:
            stay += 1
            prev_zone = zone
        stay_of.append(stay)

    groups: dict[tuple[str, str], list[int]] = {}
    for i, (d, score) in enumerate(rows):
        zone = band_of(score)[0]
        val = valuation.get(d)
        if val is not None:
            key = "valuation_extreme" if fallhoehe_label(int(round(val))) == "extrem teuer" else "valuation_other"
            groups.setdefault((zone, key), []).append(i)
        mkt = markets.get(d)
        if mkt is not None:
            confirmed = market_confirmation(int(round(score)), int(round(mkt))) == "confirmed"
            groups.setdefault((zone, "market_confirmed" if confirmed else "market_other"), []).append(i)

    out: list[ConditionalBand] = []
    for (zone, cond), idx in sorted(groups.items()):
        f13 = [fwd13[i] for i in idx if fwd13[i] is not None]
        out.append(ConditionalBand(
            zone=zone, condition=cond, label=CONDITION_LABELS[cond], weeks=len(idx),
            episodes=len({stay_of[i] for i in idx}), n_13w=len(f13),
            hit_rate_13w=round(100 * sum(1 for f in f13 if f > 0) / len(f13), 1) if f13 else None,
            mean_fwd_13w=round(100 * sum(f13) / len(f13), 2) if f13 else None,
            p10_fwd_13w=_quantile(f13, 0.10), p50_fwd_13w=_quantile(f13, 0.50),
        ))
    return out


def zone_stats(rows: list[tuple[date, float]], prices: PriceIndex, key: str, name: str) -> BenchmarkResult:
    """Zonen-Kennzahlen einer beliebigen Anlage: Trefferquote und Median der 13-Wochen-Rendite.

    Episoden sind wieder betroffene Zonenaufenthalte, damit die Zahl nicht Unabhaengigkeit vortaeuscht.
    """
    usable = [(i, d, s) for i, (d, s) in enumerate(rows) if prices.at(d) is not None]
    stay_of: dict[int, int] = {}
    prev_zone, stay = None, -1
    for i, _, score in usable:
        zone = band_of(score)[0]
        if zone != prev_zone:
            stay += 1
            prev_zone = zone
        stay_of[i] = stay

    bands: list[BenchmarkBand] = []
    for _, zkey, _label in ZONE_BANDS:
        idx = [i for i, _, score in usable if band_of(score)[0] == zkey]
        f13 = [r for r in (forward_return(prices, rows[i][0], 13) for i in idx) if r is not None]
        bands.append(BenchmarkBand(
            zone=zkey, n_13w=len(f13), episodes=len({stay_of[i] for i in idx}),
            hit_rate_13w=round(100 * sum(1 for f in f13 if f > 0) / len(f13), 1) if f13 else None,
            median_13w=_quantile(f13, 0.50),
        ))
    start = usable[0][1] if usable else rows[0][0]
    pairs = [(score, forward_return(prices, rows[i][0], 13)) for i, _, score in usable]
    valid = [(a, b) for a, b in pairs if b is not None]
    ic = round(spearman([a for a, _ in valid], [b for _, b in valid]), 3) if len(valid) >= 30 else None
    return BenchmarkResult(key=key, name=name, start=start, bands=bands, ic_13w=ic, weeks=len(usable))


def blend_index(a: PriceIndex, b: PriceIndex, dates: list[date], share_a: float) -> PriceIndex:
    """Woechentlich neu gewichtete Mischung zweier Anlagen als eigener Kursindex."""
    from .fred import Observation

    out, value = [], 100.0
    prev_a, prev_b = None, None
    for d in dates:
        pa, pb = a.at(d), b.at(d)
        if pa is None or pb is None:
            continue
        if prev_a is not None and prev_b is not None and prev_a and prev_b:
            value *= 1.0 + share_a * (pa / prev_a - 1.0) + (1.0 - share_a) * (pb / prev_b - 1.0)
        prev_a, prev_b = pa, pb
        out.append(Observation(date=d, value=value))
    return PriceIndex(out)


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
    fwd13 = [forward_return(prices, d, 13) for d, _ in ranked]
    conditional = conditional_bands(ranked, fwd13, by_date.get("valuation", {}), by_date.get("markets", {}))

    # C1: dieselbe Rechnung fuer Gold, Anleihen und eine Mischung. Faellt eine Quelle aus, fehlt nur ihre Zeile.
    benchmarks: list[BenchmarkResult] = []
    indices: dict[str, PriceIndex] = {"SPY": prices}
    for ticker, label in BENCHMARK_TICKERS:
        try:
            idx = prices if ticker == "SPY" else PriceIndex((await market.fetch_weekly_closes(ticker))[0].observations)
        except Exception as exc:  # noqa: BLE001 - ein fehlender Vergleich darf den Backtest nicht stoppen
            log.warning("Vergleichsanlage %s nicht verfuegbar: %s", ticker, exc)
            continue
        indices[ticker] = idx
        benchmarks.append(zone_stats(ranked, idx, ticker, label))
    if "IEF" in indices:
        mixed = blend_index(prices, indices["IEF"], [d for d, _ in ranked], 0.6)
        benchmarks.append(zone_stats(ranked, mixed, "MIX6040", MIXED_NAME))

    # C2: nur das Pruef-Fenster, also Wochen, die bei der Kalibrierung nicht gesehen wurden.
    test_rows = [(d, v) for d, v in ranked if d >= TEST_WINDOW_START]
    test_window = zone_stats(test_rows, prices, "SPY", f"S&P 500 ab {TEST_WINDOW_START.year}") if test_rows else None
    early_rows = [(d, v) for d, v in ranked if d < TEST_WINDOW_START]
    early_window = zone_stats(early_rows, prices, "SPY", f"S&P 500 bis {TEST_WINDOW_START.year - 1}") if early_rows else None
    report = BacktestReport(benchmark="SPY", start=raw[0][0], end=raw[-1][0], variants=variants,
                            conditional=conditional, benchmarks=benchmarks, test_window=test_window,
                            early_window=early_window, generated_at=now)
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
