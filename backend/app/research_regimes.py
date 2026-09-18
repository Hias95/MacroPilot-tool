"""Untersuchung: Haengt der Markt wirklich immer am staerksten an der Liquiditaet?

Hintergrund: Die Gewichte 55/15/30 stammen aus einer Walk-Forward-Kalibrierung ueber den ganzen Zeitraum.
Eine solche Suche mittelt ueber alle Umfelder hinweg. Sie beantwortet also die Frage "welche festen Gewichte
waren im Schnitt am besten", nicht die Frage "gibt es Lagen, in denen ein anderer Treiber wichtiger war".

Gemessen wird die Rangkorrelation (Spearman) zwischen dem Score einer Saeule und der Rendite des S&P 500 in
den folgenden 13 bzw. 26 Wochen, einmal insgesamt und einmal getrennt nach Umfeld. Wichtig fuer die Deutung:
Woechentliche Fenster ueberlappen sich stark, deshalb steht neben jeder Zahl die effektive Stichprobe.

Aufruf:  python -m app.research_regimes
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from . import fred, market
from .backtest import PriceIndex, forward_return, spearman
from .history import aligned_pillars
from .model_config import CONSENSUS_WEIGHTS

HORIZONS = (13, 26)
DRIVERS = ["liquidity", "cycle", "structure"]
OVERLAYS = ["valuation", "mechanics", "markets"]


def _ic(pairs: list[tuple[float, float]]) -> float | None:
    """Rangkorrelation, None bei zu duenner Datenlage."""
    if len(pairs) < 30:
        return None
    return round(spearman([a for a, _ in pairs], [b for _, b in pairs]), 3)


def _yoy(obs, months: int = 12) -> dict[date, float]:
    """Jahresrate einer Monatsreihe, je Beobachtungsdatum."""
    by_date = {o.date: o.value for o in obs}
    out: dict[date, float] = {}
    for o in obs:
        prev = next((v for d, v in by_date.items() if d.year == o.date.year - 1 and d.month == o.date.month), None)
        if prev:
            out[o.date] = (o.value / prev - 1.0) * 100.0
    return out


def _as_of(series: dict[date, float], d: date) -> float | None:
    """Letzter Wert am oder vor d, ohne Blick in die Zukunft."""
    candidates = [v for dd, v in series.items() if dd <= d]
    return candidates[-1] if candidates else None


async def collect() -> dict:
    """Wochenraster mit allen Scores, Vorwaertsrenditen und den Groessen fuer die Umfeld-Einteilung."""
    grid, aligned = await aligned_pillars()
    (spy, _) = await market.fetch_weekly_closes("SPY")
    prices = PriceIndex(spy.observations)
    (cpi, _) = await fred.fetch_series("CPILFESL", start=date(1995, 1, 1))
    (real, _) = await fred.fetch_series("DFII10", start=date(2003, 1, 1))
    cpi_yoy = _yoy(cpi.observations)
    real_by_date = {o.date: o.value for o in real.observations}

    rows = []
    for i, d in enumerate(grid):
        scores = {n: (aligned[n][i].score if aligned[n][i] else None) for n in aligned}
        if any(scores.get(n) is None for n in DRIVERS) or prices.at(d) is None:
            continue
        rows.append({
            "date": d,
            "scores": scores,
            "fwd": {h: forward_return(prices, d, h) for h in HORIZONS},
            "cpi": _as_of(cpi_yoy, d),
            "real": _as_of(real_by_date, d),
        })
    return {"rows": rows, "start": rows[0]["date"], "end": rows[-1]["date"]}


def blocks_of(rows: list[dict]) -> list[list[dict]]:
    """Zusammenhaengende Abschnitte; eine Luecke von mehr als einer Woche trennt."""
    out: list[list[dict]] = []
    for r in rows:
        if out and (r["date"] - out[-1][-1]["date"]).days <= 7:
            out[-1].append(r)
        else:
            out.append([r])
    return out


def effective_windows(rows: list[dict], horizon: int) -> int:
    """Zahl echt ueberschneidungsfreier Vorwaertsfenster.

    Gierig von vorn: Eine Woche nehmen, alle Wochen innerhalb des Horizonts ueberspringen, weiter. Das ist
    unbestechlich gegen beide Fehler, die vorher moeglich waren. Die Zahl der Abschnitte allein ergab fuer den
    gesamten Zeitraum eine einzige Beobachtung; die Summe ueber Abschnittslaengen zaehlte zerstreute Umfelder
    wie den Marktstress viel zu grosszuegig, weil dort jeder Einzelwoche ein eigenes Fenster zugebilligt wurde.
    """
    picked, blocked_until = 0, None
    for r in rows:
        if blocked_until is None or r["date"] >= blocked_until:
            picked += 1
            blocked_until = r["date"] + timedelta(weeks=horizon)
    return picked


def table(rows: list[dict], label: str, horizon: int = 13, period: tuple[date, date] | None = None) -> str:
    """Eine Zeile je Baustein: Rangkorrelation zum Vorwaertsertrag in diesem Umfeld."""
    if period:
        rows = [r for r in rows if period[0] <= r["date"] < period[1]]
    if len(rows) < 40:
        return f"{label:34} zu wenige Wochen ({len(rows)})"
    parts = []
    for name in DRIVERS + OVERLAYS:
        pairs = [(r["scores"][name], r["fwd"][horizon]) for r in rows
                 if r["scores"].get(name) is not None and r["fwd"][horizon] is not None]
        ic = _ic(pairs)
        parts.append(f"{name[:9]:>9} {'  n/a' if ic is None else f'{ic:+.2f}'}")
    return f"{label:34} n={len(rows):4} eff={effective_windows(rows, horizon):3} | " + " | ".join(parts)


def splits(rows: list[dict]) -> list[tuple[str, list[dict]]]:
    """Umfeld-Einteilungen, jede mit einer wirtschaftlichen Begruendung, nicht aus der Datensuche geboren.

    - Inflation: Ueber 3 Prozent Kerninflation kann die Notenbank Liquiditaet nicht frei steuern.
    - Realzins: Ist Geld real gratis, wirkt zusaetzliche Liquiditaet anders als bei positivem Realzins.
    - Bewertung: Bei hoher Fallhoehe entscheidet eher die Enttaeuschung als der Geldfluss.
    - Marktstress: In Panikphasen dominiert die Mechanik kurzfristig alles andere.
    - Konjunktur: Bricht die Realwirtschaft ein, hilft Liquiditaet erst mit Verzoegerung.
    """
    def has(key):
        return [r for r in rows if r.get(key) is not None]

    out: list[tuple[str, list[dict]]] = [("Alle Wochen", rows)]
    cpi_rows = has("cpi")
    out += [
        ("Kerninflation ueber 3 %", [r for r in cpi_rows if r["cpi"] > 3.0]),
        ("Kerninflation unter 2 %", [r for r in cpi_rows if r["cpi"] < 2.0]),
        ("Kerninflation 2 bis 3 %", [r for r in cpi_rows if 2.0 <= r["cpi"] <= 3.0]),
    ]
    real_rows = has("real")
    out += [
        ("Realzins negativ", [r for r in real_rows if r["real"] < 0]),
        ("Realzins ueber 1 %", [r for r in real_rows if r["real"] > 1.0]),
    ]
    val = [r for r in rows if r["scores"].get("valuation") is not None]
    out += [
        ("Bewertung extrem teuer (<25)", [r for r in val if r["scores"]["valuation"] < 25]),
        ("Bewertung nicht extrem (>=25)", [r for r in val if r["scores"]["valuation"] >= 25]),
    ]
    mech = [r for r in rows if r["scores"].get("mechanics") is not None]
    out += [
        ("Marktstress (Mechanik <30)", [r for r in mech if r["scores"]["mechanics"] < 30]),
        ("Ruhige Technik (Mechanik >60)", [r for r in mech if r["scores"]["mechanics"] > 60]),
    ]
    out += [
        ("Konjunktur schwach (<30)", [r for r in rows if r["scores"]["cycle"] < 30]),
        ("Konjunktur stark (>70)", [r for r in rows if r["scores"]["cycle"] > 70]),
    ]
    return [(label, rs) for label, rs in out if len(rs) >= 40]


CANDIDATES = {
    "aktuell 55/15/30": {"liquidity": 0.55, "cycle": 0.15, "structure": 0.30},
    "gleich 34/33/33": {"liquidity": 0.34, "cycle": 0.33, "structure": 0.33},
    "ausgewogen 40/15/45": {"liquidity": 0.40, "cycle": 0.15, "structure": 0.45},
    "struktur-schwer 30/15/55": {"liquidity": 0.30, "cycle": 0.15, "structure": 0.55},
    "ohne Konjunktur 50/0/50": {"liquidity": 0.50, "cycle": 0.0, "structure": 0.50},
    "nur Liquiditaet": {"liquidity": 1.0, "cycle": 0.0, "structure": 0.0},
    "nur Struktur": {"liquidity": 0.0, "cycle": 0.0, "structure": 1.0},
}


def composite_ic(rows: list[dict], weights: dict[str, float], horizon: int,
                 period: tuple[date, date] | None = None) -> float | None:
    """Rangkorrelation eines gewichteten Treiber-Mittels zum Vorwaertsertrag."""
    sel = [r for r in rows if not period or period[0] <= r["date"] < period[1]]
    pairs = [
        (sum(weights[n] * r["scores"][n] for n in DRIVERS), r["fwd"][horizon])
        for r in sel if r["fwd"][horizon] is not None and all(r["scores"].get(n) is not None for n in DRIVERS)
    ]
    return _ic(pairs)


def stability(rows: list[dict], horizon: int = 13) -> None:
    """Welche Gewichtung haelt ueber beide Zeithaelften? Der Abstand zaehlt mehr als der Mittelwert.

    Eine Gewichtung, die in einer Haelfte glaenzt und in der anderen ins Minus dreht, ist kein Modell,
    sondern eine Anpassung an die Vergangenheit.
    """
    cut = date(2018, 1, 1)
    print(f"=== Stabilitaet der Treibergewichte, {horizon} Wochen ===")
    print(f"  {'Gewichtung':26} {'gesamt':>8} {'bis 2017':>10} {'ab 2018':>9} {'Abstand':>9}")
    for label, w in CANDIDATES.items():
        full = composite_ic(rows, w, horizon)
        a = composite_ic(rows, w, horizon, (date(2000, 1, 1), cut))
        b = composite_ic(rows, w, horizon, (cut, date(2100, 1, 1)))
        gap = abs(a - b) if a is not None and b is not None else None
        fmt = lambda x: "  n/a" if x is None else f"{x:+.2f}"
        print(f"  {label:26} {fmt(full):>8} {fmt(a):>10} {fmt(b):>9} {'  n/a' if gap is None else f'{gap:.2f}':>9}")
    print()


async def live_chain_check(horizon: int = 13) -> None:
    """Dieselbe Frage noch einmal durch die echte Modellkette: Overlays, Deckel, Vetos, Rang.

    Der einfache Treiber-Mittelwert koennte die Lage verzerren. Geprueft wird deshalb, was das Tool wirklich
    anzeigt: den Rang des fertigen Rohwerts.
    """
    from .consensus import ConsensusParams, DEFAULT_PARAMS
    from .history import composite_points, rolling_rank

    grid, aligned = await aligned_pillars()
    (spy, _) = await market.fetch_weekly_closes("SPY")
    prices = PriceIndex(spy.observations)
    cut = date(2018, 1, 1)

    print(f"=== Echte Modellkette (Rang des Rohwerts), {horizon} Wochen ===")
    print(f"  {'Gewichtung':26} {'gesamt':>8} {'bis 2017':>10} {'ab 2018':>9} {'Abstand':>9}")
    for label, w in CANDIDATES.items():
        if sum(w.values()) == 0:
            continue
        # Die Zyklusphase in core() braucht die Konjunktur, auch wenn ihr Gewicht null ist. Varianten ohne
        # sie laufen deshalb nicht durch die echte Kette; das wird gesagt statt still uebersprungen.
        if w.get("cycle", 0) <= 0:
            print(f"  {label:26} nicht pruefbar: die Modellkette braucht die Konjunktur fuer die Zyklusphase")
            continue
        params = ConsensusParams(**{**DEFAULT_PARAMS.__dict__, "weights": {k: v for k, v in w.items() if v > 0}})
        points = composite_points(grid, aligned, params)
        ranks = rolling_rank([r.score for _, r in points])
        rows = [{"date": d, "rank": rk, "fwd": forward_return(prices, d, horizon)}
                for (d, _), rk in zip(points, ranks) if rk is not None]
        def ic(sel):
            pairs = [(r["rank"], r["fwd"]) for r in sel if r["fwd"] is not None]
            return _ic(pairs)
        full = ic(rows)
        a = ic([r for r in rows if r["date"] < cut])
        b = ic([r for r in rows if r["date"] >= cut])
        gap = abs(a - b) if a is not None and b is not None else None
        fmt = lambda x: "  n/a" if x is None else f"{x:+.2f}"
        print(f"  {label:26} {fmt(full):>8} {fmt(a):>10} {fmt(b):>9} {'  n/a' if gap is None else f'{gap:.2f}':>9}")
    print()


async def main() -> None:
    data = await collect()
    rows = data["rows"]
    print(f"Untersuchung Umfeld-Abhaengigkeit, {data['start']} bis {data['end']}, {len(rows)} Wochen")
    print(f"Feste Gewichte im Modell: {CONSENSUS_WEIGHTS}")
    print()
    for horizon in HORIZONS:
        print(f"=== Rangkorrelation Score gegen Rendite der folgenden {horizon} Wochen ===")
        for label, rs in splits(rows):
            print("  " + table(rs, label, horizon))
        print()

    for horizon in HORIZONS:
        stability(rows, horizon)
    await live_chain_check(13)
    await live_chain_check(26)

    # Robustheitspruefung: Ein Muster, das nur in einer Haelfte auftaucht, ist vermutlich Zufall.
    cut = date(2018, 1, 1)
    print("=== Dieselben Umfelder getrennt nach Zeitraum (13 Wochen) ===")
    for label, rs in splits(rows):
        first = table(rs, f"{label} | bis 2017", 13, (date(2000, 1, 1), cut))
        second = table(rs, f"{label} | ab 2018", 13, (cut, date(2100, 1, 1)))
        print("  " + first)
        print("  " + second)
        print()


if __name__ == "__main__":
    asyncio.run(main())
