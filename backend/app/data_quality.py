"""C3 Datenqualitaet: Pruefbericht ueber alle Rohserien, Saeulen-Serien und das Wochenraster.

Je Serie: Umfang, Abstand der Beobachtungen, Luecken, Aktualitaet, Ausreisser (robuste z-Werte der
Veraenderungen), Nullen und doppelte Termine. Je Saeule: Abdeckung auf dem Wochenraster und Abgleich
Live-Score gegen letzten Verlaufspunkt. Endpunkt /api/v1/data-quality, Text ueber
python -m app.data_quality (schreibt docs/datenqualitaet-c3-raw.txt).
"""

from __future__ import annotations

import asyncio
import statistics
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from .fred import Observation
from .history import HISTORY_PROVIDERS, MAX_AGE_DAYS, aligned_pillars
from .pillars import PROVIDERS, cycle, liquidity, markets, mechanics, structure, valuation

# Erwarteter Abstand in Tagen je Frequenz und ab wann ein Abstand als Luecke zaehlt.
GAP_LIMIT = {"daily": 10, "weekly": 21, "monthly": 45, "quarterly": 120}
STALE_LIMIT = {"daily": 10, "weekly": 14, "monthly": 50, "quarterly": 290}
OUTLIER_Z = 8.0


@dataclass
class SeriesReport:
    pillar: str
    name: str
    frequency: str
    n: int
    first: date | None
    last: date | None
    median_spacing_days: float
    max_gap_days: int
    gaps: list[tuple[date, date]]
    stale_days: int | None
    outliers: list[tuple[date, float]]
    non_positive: int
    duplicates: int
    issues: list[str] = field(default_factory=list)


@dataclass
class PillarReport:
    pillar: str
    grid_first: date | None
    grid_last: date | None
    coverage_pct: float
    longest_hole_weeks: int
    live_score: int | None
    history_last_score: int | None
    history_last_date: date | None
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityReport:
    generated_at: datetime
    series: list[SeriesReport]
    pillars: list[PillarReport]

    @property
    def issue_count(self) -> int:
        return sum(len(s.issues) for s in self.series) + sum(len(p.issues) for p in self.pillars)


def robust_outliers(obs: Sequence[Observation], z: float = OUTLIER_Z) -> list[tuple[date, float]]:
    """Veraenderungen von Punkt zu Punkt, deren robuster z-Wert (MAD) ueber z liegt."""
    if len(obs) < 30:
        return []
    # Serien, die die Null kreuzen (Diffusionsindizes, Zinsen, Kurven), werden absolut verglichen, sonst relativ.
    absolute = any(o.value <= 0 for o in obs)
    changes = []
    for a, b in zip(obs, obs[1:]):
        changes.append((b.date, b.value - a.value if absolute else (b.value - a.value) / abs(a.value)))
    vals = [c for _, c in changes]
    med = statistics.median(vals)
    mad = statistics.median(abs(v - med) for v in vals) or 1e-12
    return [(d, round(c if absolute else 100 * c, 1)) for d, c in changes if abs(c - med) / (1.4826 * mad) > z][:8]


def inspect_series(pillar: str, name: str, obs: Sequence[Observation], frequency: str, today: date) -> SeriesReport:
    dates = [o.date for o in obs]
    spacings = [(b - a).days for a, b in zip(dates, dates[1:])]
    median_spacing = float(statistics.median(spacings)) if spacings else 0.0
    limit = GAP_LIMIT[frequency]
    gaps = [(a, b) for a, b in zip(dates, dates[1:]) if (b - a).days > limit]
    # Punkte in der Zukunft (nach Verzugs-Verschiebung, z. B. laufender Shiller-Monat) zaehlen nicht als Aktualitaet.
    past = [d for d in dates if d <= today]
    stale = (today - past[-1]).days if past else None
    outliers = robust_outliers(obs)
    non_positive = sum(1 for o in obs if o.value <= 0)
    duplicates = len(dates) - len(set(dates))
    issues = []
    if not obs:
        issues.append("keine Daten")
    if gaps:
        issues.append(f"{len(gaps)} Luecken ueber {limit} Tage, groesste {max((b - a).days for a, b in gaps)} Tage")
    if stale is not None and stale > STALE_LIMIT[frequency]:
        issues.append(f"veraltet: letzter Wert vor {stale} Tagen")
    if dates and dates[-1] > today:
        issues.append(f"Vorlauf: letzter Termin {dates[-1]} liegt in der Zukunft (laufende Periode)")
    if outliers:
        issues.append(f"{len(outliers)} Ausreisser (z > {OUTLIER_Z:.0f})")
    if duplicates:
        issues.append(f"{duplicates} doppelte Termine")
    if dates != sorted(dates):
        issues.append("Termine nicht aufsteigend")
    return SeriesReport(
        pillar=pillar, name=name, frequency=frequency, n=len(obs), first=dates[0] if dates else None, last=dates[-1] if dates else None,
        median_spacing_days=median_spacing, max_gap_days=max(spacings) if spacings else 0, gaps=gaps[:5], stale_days=stale,
        outliers=outliers, non_positive=non_positive, duplicates=duplicates, issues=issues,
    )


async def collect_series(today: date) -> list[SeriesReport]:
    """Rohserien und abgeleitete Serien aller Saeulen einsammeln."""
    liq, cyc, mk, st, mech, val = await asyncio.gather(
        liquidity._data(), cycle._composite(), markets._prices(), structure._data(), mechanics._data(), valuation._data(),
    )
    items: list[tuple[str, str, Sequence[Observation], str]] = []
    for k, res in liq["raw"].items():
        items.append(("liquidity", f"FRED {res.series_id}", res.observations, "daily" if k == "rrp" else "monthly" if k == "boj" else "weekly"))
    for k in ("net", "global"):
        items.append(("liquidity", f"Serie {k}", liq["series"][k], "weekly"))
    items.append(("liquidity", "Serie tbill (MSPD)", liq["series"]["tbill"], "monthly"))
    composite, results = cyc
    for (res, _), (rid, (sid, label)) in zip(results, cycle.REGIONS.items()):
        items.append(("cycle", f"FRED {sid} ({label})", res.observations, "monthly"))
    items.append(("cycle", "Composite", composite, "monthly"))
    for t, r in sorted(mk.items()):
        items.append(("markets", f"Yahoo {t}", r.observations, "weekly"))
    for s in markets.SIGNALS:
        items.append(("markets", f"Signal {s.id}", markets._series(mk, s), "weekly"))
    for sid, res in st["raw"].items():
        freq = "daily" if sid in ("T10Y2Y", "DFII10", "DGS10") else "quarterly" if sid in ("TDSP", "A091RC1Q027SBEA", "W006RC1Q027SBEA") else "monthly"
        items.append(("structure", f"FRED {sid}", res.observations, freq))
    for k, obs in st["series"].items():
        items.append(("structure", f"Serie {k}", obs, "weekly" if k in ("curve", "real") else "quarterly" if k in ("dsr", "interest") else "monthly"))
    for k, obs in mech["series"].items():
        items.append(("mechanics", f"Serie {k}", obs, "weekly"))
    for k, obs in val["series"].items():
        items.append(("valuation", f"Serie {k}", obs, "quarterly" if k == "buffett" else "monthly"))
    return [inspect_series(p, n, o, f, today) for p, n, o, f in items]


async def collect_pillars(today: date) -> list[PillarReport]:
    grid, aligned = await aligned_pillars()
    live = dict(zip(PROVIDERS, await asyncio.gather(*(PROVIDERS[p]() for p in PROVIDERS))))
    histories = dict(zip(HISTORY_PROVIDERS, await asyncio.gather(*(HISTORY_PROVIDERS[n]() for n in HISTORY_PROVIDERS))))
    out: list[PillarReport] = []
    for name in HISTORY_PROVIDERS:
        pts = aligned[name]
        idx = [i for i, p in enumerate(pts) if p is not None]
        if not idx:
            out.append(PillarReport(name, None, None, 0.0, 0, None, None, None, ["keine Punkte auf dem Raster"]))
            continue
        span = pts[idx[0]:]
        holes = [i for i, p in enumerate(span) if p is None]
        longest, run = 0, 0
        for p in span:
            run = run + 1 if p is None else 0
            longest = max(longest, run)
        coverage = 100.0 * (len(span) - len(holes)) / len(span)
        live_score = live[name].score.score if live[name].score else None
        hist = histories[name]
        last = hist[-1] if hist else None
        issues = []
        if coverage < 98:
            issues.append(f"Abdeckung nur {coverage:.1f} % (max. Alter {MAX_AGE_DAYS[name]} Tage)")
        if longest >= 4:
            issues.append(f"laengste Luecke {longest} Wochen")
        if live_score is not None and last is not None and abs(live_score - last.score) > 5:
            issues.append(f"Live-Score {live_score} weicht vom letzten Verlaufspunkt {last.score} ({last.date}) um mehr als 5 ab")
        if last is not None and (today - last.date).days > STALE_LIMIT["monthly"]:
            issues.append(f"Verlauf endet vor {(today - last.date).days} Tagen")
        out.append(PillarReport(name, grid[idx[0]], grid[idx[-1]], round(coverage, 1), longest, live_score,
                                last.score if last else None, last.date if last else None, issues))
    return out


async def run_audit() -> QualityReport:
    today = date.today()
    series, pillars = await asyncio.gather(collect_series(today), collect_pillars(today))
    return QualityReport(generated_at=datetime.now(tz=timezone.utc), series=series, pillars=pillars)


def format_report(rep: QualityReport) -> str:
    L = [f"Datenqualitaet, Stand {rep.generated_at:%Y-%m-%d %H:%M} UTC, {rep.issue_count} Auffaelligkeiten", ""]
    for s in rep.series:
        flag = "!!" if s.issues else "ok"
        L.append(f"[{flag}] {s.pillar:10s} {s.name:34s} n={s.n:5d} {s.first} .. {s.last} | Abstand {s.median_spacing_days:.0f} T, max {s.max_gap_days} T | alt {s.stale_days} T")
        for i in s.issues:
            L.append(f"        - {i}")
        for d, pct in s.outliers[:4]:
            L.append(f"        Ausreisser {d}: {pct:+.1f} (Prozent, bei Serien um null absolut)")
        for a, b in s.gaps[:3]:
            L.append(f"        Luecke {a} .. {b}")
    L.append("")
    for p in rep.pillars:
        flag = "!!" if p.issues else "ok"
        L.append(f"[{flag}] Saeule {p.pillar:10s} Raster {p.grid_first} .. {p.grid_last} | Abdeckung {p.coverage_pct} % | laengste Luecke {p.longest_hole_weeks} W | live {p.live_score} vs Verlauf {p.history_last_score} ({p.history_last_date})")
        for i in p.issues:
            L.append(f"        - {i}")
    return "\n".join(L)


def to_dict(rep: QualityReport) -> dict:
    return {"generated_at": rep.generated_at, "issue_count": rep.issue_count,
            "series": [asdict(s) for s in rep.series], "pillars": [asdict(p) for p in rep.pillars]}


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "docs" / "datenqualitaet-c3-raw.txt"
    report = asyncio.run(run_audit())
    text = format_report(report)
    target.write_text(text, encoding="utf-8")
    print(text.encode("ascii", "replace").decode())
