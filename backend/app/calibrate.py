"""Kalibrierung C2: Walk-Forward ueber die Consensus-Parameter.

Lernfenster: Rang-Wochen vor TRAIN_END, Pruef-Fenster danach. Ziel im Lernfenster ist das Mittel aus IC13 und
IC26 (Spearman-Rangkorrelation des Consensus-Rangs mit den SPY-Vorwaertsrenditen). Das Pruef-Fenster wird nur
berichtet, nie zur Auswahl genutzt. Stufe 1: Treibergewichte (Schritt 0,1) x Liquiditaets-Momentum {13, 26, 52}
x Mechanik-Spanne {-5, 0, +5}. Stufe 2: um die besten Gewichte Schritt 0,05 plus Bewertungs-Deckel, Vetos und
Marktsignale invers. Aufruf: python -m app.calibrate  (schreibt docs/backtest-c2-raw.txt).
"""

from __future__ import annotations

import asyncio
import sys
import time
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from . import fred, market
from .backtest import EXPOSURE_BASE, EXPOSURE_DEFENSIVE, PriceIndex, _strategy, band_of, forward_return, spearman
from .consensus import DEFAULT_PARAMS, ConsensusParams
from .history import MAX_AGE_DAYS, aligned_pillars, composite_points, rolling_rank
from .model_config import CONSENSUS_WEIGHTS, LIQUIDITY, LIQUIDITY_GLOBAL, LIQUIDITY_TBILL, LIQUIDITY_WEIGHTS, MECHANICS_RANGE, ZONE_BANDS
from .pillars import liquidity
from .pillars.common import average_points, forward_fill
from .scoring import ScorePoint, score_history

TRAIN_END = date(2019, 1, 1)
HORIZONS = (4, 13, 26, 52)
DRIVERS = ("liquidity", "markets", "cycle", "structure")
CAP_OFF = {"base": 100.0, "slope": 0.0}
VETO_OFF = {"liquidity_below": -1, "liquidity_cap": 100, "structure_below": -1, "structure_cap": 100,
            "mechanics_below": -1, "valuation_mechanics_cap": 100}


@dataclass(frozen=True)
class Config:
    weights: tuple[float, float, float, float]  # liquidity, markets, cycle, structure
    liq_momentum: int = 13
    mechanics_range: float = 5.0
    cap: bool = True
    vetoes: bool = True
    markets_sign: int = 1

    def params(self) -> ConsensusParams:
        return ConsensusParams(
            weights=dict(zip(DRIVERS, self.weights)), mechanics_range=self.mechanics_range,
            valuation_cap=dict(DEFAULT_PARAMS.valuation_cap) if self.cap else dict(CAP_OFF),
            vetoes=dict(DEFAULT_PARAMS.vetoes) if self.vetoes else dict(VETO_OFF), markets_sign=self.markets_sign,
        )

    def label(self) -> str:
        w = "/".join(f"{x:.2f}" for x in self.weights)
        return (f"W {w} | Liq {self.liq_momentum}W | Mech {self.mechanics_range:+.0f} | Deckel {'an' if self.cap else 'aus'}"
                f" | Vetos {'an' if self.vetoes else 'aus'} | Maerkte {'invers' if self.markets_sign < 0 else 'normal'}")


@dataclass
class Metrics:
    n_train: int
    n_test: int
    ic_train: dict[int, float]
    ic_test: dict[int, float]

    @property
    def objective(self) -> float:
        return round((self.ic_train[13] + self.ic_train[26]) / 2, 3)

    @property
    def objective_test(self) -> float:
        return round((self.ic_test[13] + self.ic_test[26]) / 2, 3)

    def line(self) -> str:
        t, p = self.ic_train, self.ic_test
        return (f"Lernen {self.objective:+.3f} (IC4 {t[4]:+.2f} 13 {t[13]:+.2f} 26 {t[26]:+.2f} 52 {t[52]:+.2f}) | "
                f"Pruefen {self.objective_test:+.3f} (IC4 {p[4]:+.2f} 13 {p[13]:+.2f} 26 {p[26]:+.2f} 52 {p[52]:+.2f})")


# Aktuelle Parameter aus model_config als Referenz; die Suche laeuft unabhaengig davon.
BASELINE = Config(weights=tuple(CONSENSUS_WEIGHTS.get(k, 0.0) for k in DRIVERS), liq_momentum=LIQUIDITY.momentum_window,  # type: ignore[arg-type]
                  mechanics_range=MECHANICS_RANGE)


def weight_grid(step: int = 10) -> list[tuple[float, float, float, float]]:
    """Alle Gewichtsvektoren mit Summe 1 in Schritten von 1/step."""
    out = []
    for a in range(step + 1):
        for b in range(step + 1 - a):
            for c in range(step + 1 - a - b):
                d = step - a - b - c
                out.append(tuple(round(x / step, 2) for x in (a, b, c, d)))
    return out  # type: ignore[return-value]


def neighbours(w: tuple[float, ...], radius: float = 0.1, step: float = 0.05) -> list[tuple[float, float, float, float]]:
    """Gewichte in der Naehe von w (Summe 1, alle >= 0), Schritt 0,05."""
    grid = weight_grid(int(round(1 / step)))
    return [g for g in grid if all(abs(a - b) <= radius + 1e-9 for a, b in zip(g, w))]  # type: ignore[misc]


class Calibrator:
    def __init__(self, grid: list[date], aligned: dict[str, list[ScorePoint | None]], prices: PriceIndex, cash: PriceIndex) -> None:
        self.grid, self.base_aligned, self.prices, self.cash = grid, aligned, prices, cash
        self.fwd = {h: {d: forward_return(prices, d, h) for d in grid} for h in HORIZONS}
        self.liq_variants: dict[int, list[ScorePoint | None]] = {LIQUIDITY.momentum_window: aligned["liquidity"]}
        self.evals = 0

    async def prepare_liquidity(self, windows: tuple[int, ...]) -> None:
        """Liquiditaets-Saeule mit anderem Momentum-Fenster (Wochen; T-Bill-Anteil in Monaten skaliert)."""
        d = await liquidity._data()
        for w in windows:
            if w in self.liq_variants:
                continue
            months = max(1, round(w / 4.33))
            params = {"net": replace(LIQUIDITY, momentum_window=w), "global": replace(LIQUIDITY_GLOBAL, momentum_window=w),
                      "tbill": replace(LIQUIDITY_TBILL, momentum_window=months)}
            hist = {k: score_history(d["history_series"][k], **params[k].history_kwargs()) for k in params}
            pts = average_points(hist["net"], [hist["global"], hist["tbill"]], max_age_days=[21, 62],
                                 weights=[LIQUIDITY_WEIGHTS[k] for k in ("net", "global", "tbill")])
            self.liq_variants[w] = forward_fill(pts, self.grid, MAX_AGE_DAYS["liquidity"])

    def rank_rows(self, cfg: Config) -> list[tuple[date, float]]:
        aligned = dict(self.base_aligned)
        aligned["liquidity"] = self.liq_variants[cfg.liq_momentum]
        pts = composite_points(self.grid, aligned, cfg.params())
        ranks = rolling_rank([r.score for _, r in pts])
        return [(d, rk) for (d, _), rk in zip(pts, ranks) if rk is not None and self.prices.at(d) is not None]

    def _ic(self, rows: list[tuple[date, float]]) -> dict[int, float]:
        out = {}
        for h in HORIZONS:
            pairs = [(s, self.fwd[h][d]) for d, s in rows if self.fwd[h][d] is not None]
            out[h] = round(spearman([a for a, _ in pairs], [b for _, b in pairs]), 3) if len(pairs) > 20 else 0.0
        return out

    def evaluate(self, cfg: Config) -> Metrics:
        self.evals += 1
        rows = self.rank_rows(cfg)
        train = [(d, s) for d, s in rows if d < TRAIN_END]
        test = [(d, s) for d, s in rows if d >= TRAIN_END]
        return Metrics(len(train), len(test), self._ic(train), self._ic(test))

    def detail(self, cfg: Config) -> list[str]:
        """Zonen und Strategie im Pruef-Fenster sowie ueber alles, fuer die Finalisten."""
        rows = self.rank_rows(cfg)
        lines = []
        for name, sub in (("Pruefen ab 2019", [r for r in rows if r[0] >= TRAIN_END]), ("Gesamt", rows)):
            zone_txt = []
            for _, key, label in ZONE_BANDS:
                idx = [d for d, s in sub if band_of(s)[0] == key]
                f13 = [self.fwd[13][d] for d in idx if self.fwd[13][d] is not None]
                if f13:
                    zone_txt.append(f"{label} {100 * len(idx) / len(sub):.0f}% -> {100 * sum(f13) / len(f13):+.1f}% "
                                    f"({100 * sum(1 for x in f13 if x > 0) / len(f13):.0f}% Treffer)")
                else:
                    zone_txt.append(f"{label} {100 * len(idx) / len(sub):.0f}% -> n/a")
            base = _strategy(sub, self.prices, self.cash, lambda s: EXPOSURE_BASE[band_of(s)[0]])
            defensive = _strategy(sub, self.prices, self.cash, lambda s: EXPOSURE_DEFENSIVE[band_of(s)[0]])
            bh = _strategy(sub, self.prices, self.cash, lambda s: 1.0)
            lines.append(f"   {name} ({len(sub)} Wochen): 13-Wochen-Rendite je Zone: " + " | ".join(zone_txt))
            lines.append(f"   {name}: Basis CAGR {base.cagr_pct}% Sharpe {base.sharpe} DD {base.max_drawdown_pct}% | "
                         f"defensiv CAGR {defensive.cagr_pct}% Sharpe {defensive.sharpe} DD {defensive.max_drawdown_pct}% | "
                         f"Buy&Hold CAGR {bh.cagr_pct}% Sharpe {bh.sharpe} DD {bh.max_drawdown_pct}% | Zonenwechsel/Jahr {base.band_changes_per_year}")
        return lines


def _marginals(results: list[tuple[Config, Metrics]], key, name: str) -> list[str]:
    groups: dict = {}
    for cfg, m in results:
        groups.setdefault(key(cfg), []).append(m)
    lines = [f"   {name}:"]
    for k in sorted(groups):
        ms = groups[k]
        best = max(ms, key=lambda x: x.objective)
        lines.append(f"      {k!s:>6}: Mittel Lernen {sum(x.objective for x in ms) / len(ms):+.3f}, bestes Lernen {best.objective:+.3f} "
                     f"(dessen Pruefen {best.objective_test:+.3f}), Mittel Pruefen {sum(x.objective_test for x in ms) / len(ms):+.3f}")
    return lines


async def run(out_path: Path | None = None, log=print) -> str:
    t0 = time.time()
    grid, aligned = await aligned_pillars()
    (spy, _), (tb, _) = await market.fetch_weekly_closes("SPY"), await fred.fetch_series("WTB3MS", start=date(2000, 1, 1))
    cal = Calibrator(grid, aligned, PriceIndex(spy.observations), PriceIndex(tb.observations))
    liq_windows = (13, 26, 52)
    await cal.prepare_liquidity(liq_windows)
    log(f"Daten geladen in {time.time() - t0:.0f}s")

    base_m = cal.evaluate(BASELINE)
    lines = [f"Kalibrierung C2, Walk-Forward. Lernen bis {TRAIN_END}, Pruefen danach. Ziel = Mittel aus IC13 und IC26 im Lernfenster.",
             f"Rang-Wochen: {base_m.n_train} Lernen, {base_m.n_test} Pruefen.", "",
             f"Basis (aktuelle Parameter): {BASELINE.label()}", f"   {base_m.line()}", *cal.detail(BASELINE), ""]

    # Stufe 1: Gewichte x Liquiditaets-Momentum x Mechanik-Spanne, Deckel und Vetos an, Maerkte normal.
    stage1: list[tuple[Config, Metrics]] = []
    t1 = time.time()
    for w in weight_grid(10):
        for lw in liq_windows:
            for mech in (-5.0, 0.0, 5.0):
                cfg = Config(weights=w, liq_momentum=lw, mechanics_range=mech)
                stage1.append((cfg, cal.evaluate(cfg)))
    stage1.sort(key=lambda x: x[1].objective, reverse=True)
    log(f"Stufe 1: {len(stage1)} Konfigurationen in {time.time() - t1:.0f}s")
    lines += [f"Stufe 1: {len(stage1)} Konfigurationen (Gewichte Schritt 0,1 x Liquiditaets-Momentum x Mechanik). Top 12 nach Lernfenster:"]
    for cfg, m in stage1[:12]:
        lines.append(f"   {cfg.label()}\n      {m.line()}")
    lines += ["", "Randeffekte Stufe 1 (je Parameterwert ueber alle anderen Kombinationen):"]
    lines += _marginals(stage1, lambda c: c.liq_momentum, "Liquiditaets-Momentum (Wochen)")
    lines += _marginals(stage1, lambda c: c.mechanics_range, "Mechanik-Spanne")
    for i, name in enumerate(("Gewicht Liquiditaet", "Gewicht Marktsignale", "Gewicht Konjunktur", "Gewicht Struktur")):
        lines += _marginals(stage1, lambda c, i=i: c.weights[i], name)
    lines.append("")

    # Stufe 2: um die besten fuenf Gewichtsvektoren feiner suchen, dazu Deckel, Vetos, Maerkte invers.
    seeds: list[Config] = []
    for cfg, _ in stage1:
        if all(cfg.weights != s.weights for s in seeds):
            seeds.append(cfg)
        if len(seeds) == 5:
            break
    seen: set[Config] = set()
    stage2: list[tuple[Config, Metrics]] = []
    t2 = time.time()
    for seed in seeds:
        for w in neighbours(seed.weights):
            for cap in (True, False):
                for vet in (True, False):
                    for sign in (1, -1):
                        cfg = Config(weights=w, liq_momentum=seed.liq_momentum, mechanics_range=seed.mechanics_range,
                                     cap=cap, vetoes=vet, markets_sign=sign)
                        if cfg in seen:
                            continue
                        seen.add(cfg)
                        stage2.append((cfg, cal.evaluate(cfg)))
    stage2.sort(key=lambda x: x[1].objective, reverse=True)
    log(f"Stufe 2: {len(stage2)} Konfigurationen in {time.time() - t2:.0f}s")
    lines += [f"Stufe 2: {len(stage2)} Konfigurationen (Schritt 0,05 um die Top-5-Gewichte x Deckel x Vetos x Maerkte invers). Top 12:"]
    for cfg, m in stage2[:12]:
        lines.append(f"   {cfg.label()}\n      {m.line()}")
    lines += ["", "Randeffekte Stufe 2:"]
    lines += _marginals(stage2, lambda c: c.cap, "Bewertungs-Deckel an")
    lines += _marginals(stage2, lambda c: c.vetoes, "Vetos an")
    lines += _marginals(stage2, lambda c: c.markets_sign, "Marktsignale Vorzeichen")
    lines.append("")

    # Finalisten: Top 3 aus Stufe 2 plus die beste Konfiguration mit unveraendertem Deckel/Vetos/Vorzeichen.
    finalists = [cfg for cfg, _ in stage2[:3]]
    plain = next((cfg for cfg, _ in stage2 if cfg.cap and cfg.vetoes and cfg.markets_sign == 1), None)
    if plain and plain not in finalists:
        finalists.append(plain)
    lines.append("Finalisten im Detail (Zonen und Strategie im Pruef-Fenster und gesamt):")
    for cfg in finalists:
        m = cal.evaluate(cfg)
        lines += [f"   {cfg.label()}", f"      {m.line()}", *cal.detail(cfg), ""]
    lines.append(f"{cal.evals} Auswertungen, {time.time() - t0:.0f}s gesamt.")
    text = "\n".join(lines)
    if out_path:
        out_path.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "docs" / "backtest-c2-raw.txt"
    report = asyncio.run(run(target, log=lambda s: print(s, file=sys.stderr, flush=True)))
    print(report)
