"""Forschung: Welche Rolle tragen die Marktsignale (Breite, Risikoappetit, Kupfer/Gold, Kredit) wirklich?

Getestet gegen SPY-Vorwaertsrenditen (4/13/26/52 Wochen) und den Drawdown der naechsten 13 Wochen:
  1. Einzelsignale und Parametrisierungen (Niveau, Momentum, Fenster) als Vorhersager.
  2. Divergenz Markt gegen Makro-Kern (Liquiditaet, Konjunktur, Struktur ohne Marktsignale).
  3. Extremzonen (Kapitulation) als Kontra-Signal.
  4. Drawdown-Warnung: Verteilung der Folgerenditen je Marktsignal-Quintil.
  5. Strategie-Varianten: Makro-Kern-Zonen mit Markt-Regeln.
Aufruf: python -m app.research_markets  (schreibt docs/marktsignale-analyse-raw.txt).
"""

from __future__ import annotations

import asyncio
import sys
from bisect import bisect_right
from dataclasses import replace
from datetime import date
from pathlib import Path

from . import fred, market
from .backtest import EXPOSURE_BASE, PriceIndex, _strategy, band_of, forward_return, percentile, spearman
from .consensus import DEFAULT_PARAMS, ConsensusParams
from .history import MAX_AGE_DAYS, aligned_pillars, composite_points, rolling_rank
from .model_config import MARKETS
from .pillars import markets
from .pillars.common import average_points, forward_fill
from .scoring import ScorePoint, score_history

HORIZONS = (4, 13, 26, 52)
TEST_START = date(2019, 1, 1)
MACRO3 = ConsensusParams(weights={"liquidity": 0.5, "markets": 0.0, "cycle": 0.15, "structure": 0.25})


class Lab:
    def __init__(self, grid, aligned, prices: PriceIndex, cash: PriceIndex):
        self.grid, self.aligned, self.prices, self.cash = grid, aligned, prices, cash
        self.fwd = {h: {d: forward_return(prices, d, h) for d in grid} for h in HORIZONS}
        self.dd13 = {d: self._drawdown(d, 13) for d in grid}

    def _drawdown(self, d: date, weeks: int) -> float | None:
        i = bisect_right(self.prices.dates, d) - 1
        if i < 0 or i + weeks >= len(self.prices.values):
            return None
        p0 = self.prices.values[i]
        return min(self.prices.values[i + 1:i + 1 + weeks]) / p0 - 1.0

    def ic(self, rows: list[tuple[date, float]]) -> str:
        out = []
        for h in HORIZONS:
            pairs = [(s, self.fwd[h][d]) for d, s in rows if self.fwd[h][d] is not None]
            out.append(f"{h}W {spearman([a for a, _ in pairs], [b for _, b in pairs]):+.3f}" if len(pairs) > 30 else f"{h}W n/a")
        return " | ".join(out)

    def cond(self, rows: list[tuple[date, float]], label: str) -> str:
        """Bedingte Folgerenditen einer Teilmenge: Anzahl, Mittel 13/26 W, Trefferquote, P10 und mittlerer Drawdown 13 W."""
        f13 = [self.fwd[13][d] for d, _ in rows if self.fwd[13][d] is not None]
        f26 = [self.fwd[26][d] for d, _ in rows if self.fwd[26][d] is not None]
        dd = [self.dd13[d] for d, _ in rows if self.dd13[d] is not None]
        if len(f13) < 5:
            return f"   {label}: {len(rows)} Wochen, zu wenig Daten"
        p10 = percentile(sorted(f13), 0.1)
        return (f"   {label}: {len(rows)} Wochen | 13W {100 * sum(f13) / len(f13):+.1f}% (Treffer {100 * sum(x > 0 for x in f13) / len(f13):.0f}%, "
                f"P10 {100 * p10:+.1f}%, unter -10%: {100 * sum(x < -0.1 for x in f13) / len(f13):.0f}%) | 26W {100 * sum(f26) / max(1, len(f26)):+.1f}% | "
                f"Drawdown 13W im Mittel {100 * sum(dd) / max(1, len(dd)):+.1f}%")

    def quintiles(self, rows: list[tuple[date, float]], name: str) -> list[str]:
        order = sorted(rows, key=lambda r: r[1])
        lines = [f"   {name}: Quintile (niedrig bis hoch)"]
        for q in range(5):
            chunk = order[q * len(order) // 5:(q + 1) * len(order) // 5]
            lo, hi = chunk[0][1], chunk[-1][1]
            lines.append(self.cond(chunk, f"Q{q + 1} ({lo:.0f} bis {hi:.0f})"))
        return lines

    def strategy_line(self, rows: list[tuple[date, float]], exposure_of, name: str) -> str:
        full = _strategy(rows, self.prices, self.cash, exposure_of)
        test_rows = [r for r in rows if r[0] >= TEST_START]
        test = _strategy(test_rows, self.prices, self.cash, exposure_of)
        return (f"   {name}: gesamt CAGR {full.cagr_pct}% Sharpe {full.sharpe} DD {full.max_drawdown_pct}% Exp {full.avg_exposure} | "
                f"ab 2019 CAGR {test.cagr_pct}% Sharpe {test.sharpe} DD {test.max_drawdown_pct}%")


def on_grid(points: list[ScorePoint], grid: list[date], max_age: int = 21) -> list[tuple[date, ScorePoint]]:
    return [(d, p) for d, p in zip(grid, forward_fill(points, grid, max_age)) if p]


def as_rows(pairs: list[tuple[date, ScorePoint]], attr: str = "score") -> list[tuple[date, float]]:
    return [(d, float(getattr(p, attr))) for d, p in pairs]


async def run(out_path: Path | None = None) -> str:
    grid, aligned = await aligned_pillars()
    (spy, _), (tb, _) = await market.fetch_weekly_closes("SPY"), await fred.fetch_series("WTB3MS", start=date(2000, 1, 1))
    lab = Lab(grid, aligned, PriceIndex(spy.observations), PriceIndex(tb.observations))
    prices = await markets._prices()
    series = {s.id: markets._series(prices, s) for s in markets.SIGNALS}
    L: list[str] = ["Marktsignale: welche Rolle traegt Information? SPY-Vorwaertsrenditen, Wochenraster, kein Blick in die Zukunft.", ""]

    # 1. Einzelsignale und Parametrisierungen
    L.append("1. Rangkorrelation (IC) je Einzelsignal und Parametrisierung")
    variants = {
        "Standard (40% Niveau 5J, 60% Momentum 13W)": MARKETS,
        "nur Niveau 5J": replace(MARKETS, level_weight=1.0),
        "nur Momentum 13W": replace(MARKETS, level_weight=0.0),
        "nur Momentum 26W": replace(MARKETS, level_weight=0.0, momentum_window=26),
        "nur Momentum 52W": replace(MARKETS, level_weight=0.0, momentum_window=52),
        "Niveau 10J + Momentum 26W": replace(MARKETS, lookback=520, momentum_window=26),
    }
    per_signal: dict[str, dict[str, list[tuple[date, ScorePoint]]]] = {}
    for vname, params in variants.items():
        L.append(f"   [{vname}]")
        hists = {s.id: score_history(series[s.id], **params.history_kwargs()) for s in markets.SIGNALS}
        per_signal[vname] = {sid: on_grid(h, grid) for sid, h in hists.items()}
        for s in markets.SIGNALS:
            L.append(f"      {s.id:8s} {lab.ic(as_rows(per_signal[vname][s.id]))}")
        comp = average_points(hists["breadth"], [hists["risk"], hists["real"], hists["credit"]], max_age_days=21)
        L.append(f"      {'Mittel':8s} {lab.ic(as_rows(on_grid(comp, grid)))}")
    L.append("")

    # 2. Makro-Kern (ohne Marktsignale) und Divergenz
    macro = composite_points(grid, aligned, MACRO3)
    macro_rank = [(d, r) for (d, _), r in zip(macro, rolling_rank([r.score for _, r in macro])) if r is not None]
    mk = as_rows([(d, p) for d, p in zip(grid, aligned["markets"]) if p])
    mk_rank = [(d, r) for (d, _), r in zip(mk, rolling_rank([s for _, s in mk])) if r is not None]
    by_date_mk = dict(mk); by_date_mkr = dict(mk_rank); by_date_macro = dict(macro_rank)
    common = [d for d, _ in macro_rank if d in by_date_mkr and lab.prices.at(d) is not None]
    L.append(f"2. Makro-Kern (Liquiditaet 50 / Konjunktur 15 / Struktur 25, Rang 10J) gegen Marktsignale, {len(common)} gemeinsame Wochen")
    L.append(f"   Makro-Kern-Rang allein:      {lab.ic([(d, by_date_macro[d]) for d in common])}")
    L.append(f"   Marktsignal-Score allein:    {lab.ic([(d, by_date_mk[d]) for d in common])}")
    L.append(f"   Marktsignal-Rang 10J allein: {lab.ic([(d, by_date_mkr[d]) for d in common])}")
    L.append(f"   Divergenz Markt minus Makro: {lab.ic([(d, by_date_mkr[d] - by_date_macro[d]) for d in common])}")
    L.append("   Quadranten (Makro-Rang / Markt-Rang, Grenze 50):")
    for mlab, mcond in (("Makro hoch", lambda g: g >= 50), ("Makro tief", lambda g: g < 50)):
        for klab, kcond in (("Markt hoch", lambda k: k >= 50), ("Markt tief", lambda k: k < 50)):
            rows = [(d, 0.0) for d in common if mcond(by_date_macro[d]) and kcond(by_date_mkr[d])]
            L.append(lab.cond(rows, f"{mlab} + {klab}"))
    L.append("   Makro-Rang in Terzilen, je nach Markt-Bestaetigung (Markt-Rang >= 50):")
    for lo, hi, name in ((0, 33, "Makro unteres Drittel"), (33, 67, "Makro Mitte"), (67, 101, "Makro oberes Drittel")):
        for klab, kcond in (("Markt bestaetigt", lambda k: k >= 50), ("Markt widerspricht", lambda k: k < 50)):
            rows = [(d, 0.0) for d in common if lo <= by_date_macro[d] < hi and kcond(by_date_mkr[d])]
            L.append(lab.cond(rows, f"{name}, {klab}"))
    L.append("")

    # 3. Extremzonen als Kontra-Signal
    L.append("3. Extremzonen der Marktsignale (Kapitulation) als Kontra-Signal")
    mk_pts = [(d, p) for d, p in zip(grid, aligned["markets"]) if p and lab.prices.at(d) is not None]
    for name, cond in (("Score < 15", lambda p: p.score < 15), ("Score < 20", lambda p: p.score < 20), ("Score < 25", lambda p: p.score < 25),
                       ("Niveau < 10", lambda p: p.level < 10), ("Momentum < 10", lambda p: p.momentum < 10),
                       ("Score > 75", lambda p: p.score > 75), ("Score > 80", lambda p: p.score > 80)):
        rows = [(d, 0.0) for d, p in mk_pts if cond(p)]
        L.append(lab.cond(rows, name))
    credit = per_signal["Standard (40% Niveau 5J, 60% Momentum 13W)"]["credit"]
    L.append("   Kredit (HYG/IEF) allein:")
    for name, cond in (("Kredit-Score < 20", lambda p: p.score < 20), ("Kredit-Momentum < 10", lambda p: p.momentum < 10),
                       ("Kredit-Niveau < 10", lambda p: p.level < 10), ("Kredit-Score > 80", lambda p: p.score > 80)):
        L.append(lab.cond([(d, 0.0) for d, p in credit if cond(p) and lab.prices.at(d) is not None], name))
    L.append("")

    # 4. Drawdown-Warnung: Verteilung je Quintil
    L.append("4. Drawdown-Warnung: Verteilung der Folgerenditen je Quintil")
    L += lab.quintiles([(d, float(p.score)) for d, p in mk_pts], "Marktsignal-Score")
    L += lab.quintiles([(d, float(p.score)) for d, p in credit if lab.prices.at(d) is not None], "Kredit-Score")
    L += lab.quintiles([(d, by_date_macro[d]) for d in common], "Makro-Kern-Rang")
    L.append("")

    # 5. Strategien: Makro-Kern-Zonen (Basis-Quoten) plus Markt-Regeln
    L.append("5. Strategien auf den Makro-Kern-Zonen (Basis-Quoten 50/70/85/100/100) plus Markt-Regeln")
    cur = composite_points(grid, aligned, DEFAULT_PARAMS)
    cur_rank = [(d, r) for (d, _), r in zip(cur, rolling_rank([r.score for _, r in cur])) if r is not None and lab.prices.at(d) is not None]
    base_rows = [(d, r) for d, r in macro_rank if lab.prices.at(d) is not None]
    mkp = {d: p for d, p in mk_pts}
    crd = {d: p for d, p in credit}
    base = lambda s: EXPOSURE_BASE[band_of(s)[0]]
    L.append(lab.strategy_line(cur_rank, base, "Consensus aktuell (Marktsignale 10%)"))
    L.append(lab.strategy_line(base_rows, base, "Makro-Kern ohne Marktsignale"))
    L.append(lab.strategy_line(base_rows, lambda s: 1.0, "Buy and Hold"))
    def with_rule(rule):
        def f(d: date, s: float) -> float:
            return rule(base(s), mkp.get(d), crd.get(d))
        return f
    rules = {
        "Kapitulation: Markt-Score < 20 -> voll investiert": lambda e, m, c: 1.0 if m and m.score < 20 else e,
        "Risk-off: Markt-Score < 30 -> Quote x0,5": lambda e, m, c: e * 0.5 if m and m.score < 30 else e,
        "Risk-off: Kredit-Momentum < 10 -> Quote x0,5": lambda e, m, c: e * 0.5 if c and c.momentum < 10 else e,
        "Bestaetigung: Markt-Score >= 50 -> +0,15 Quote, sonst -0,15": lambda e, m, c: min(1.0, e + 0.15) if m and m.score >= 50 else max(0.0, e - 0.15),
        "Kapitulation < 20 voll + Kredit-Momentum < 10 halb": lambda e, m, c: 1.0 if m and m.score < 20 else (e * 0.5 if c and c.momentum < 10 else e),
    }
    for name, rule in rules.items():
        f = with_rule(rule)
        L.append(_strategy_dated(lab, base_rows, f, name))
    text = "\n".join(L)
    if out_path:
        out_path.write_text(text, encoding="utf-8")
    return text


def _strategy_dated(lab: Lab, rows, f, name: str) -> str:
    """_strategy kennt nur den Score; die Regel braucht das Datum, deshalb wird es ueber einen Index eingeschleust."""
    idx = {s_id: d for s_id, (d, _) in enumerate(rows)}
    coded = [(d, float(i)) for i, (d, _) in enumerate(rows)]
    score_of = {i: s for i, (_, s) in enumerate(rows)}
    exposure_of = lambda code: f(idx[int(code)], score_of[int(code)])
    full = _strategy(coded, lab.prices, lab.cash, exposure_of)
    test = [(d, c) for d, c in coded if d >= TEST_START]
    t = _strategy(test, lab.prices, lab.cash, exposure_of)
    return (f"   {name}: gesamt CAGR {full.cagr_pct}% Sharpe {full.sharpe} DD {full.max_drawdown_pct}% Exp {full.avg_exposure} | "
            f"ab 2019 CAGR {t.cagr_pct}% Sharpe {t.sharpe} DD {t.max_drawdown_pct}%")


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "docs" / "marktsignale-analyse-raw.txt"
    print(asyncio.run(run(target)).encode("ascii", "replace").decode())
