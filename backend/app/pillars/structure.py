"""Saeule 4 - Struktur & Fiskus (Denkschulen Ray Dalio, Russell Napier): Wie viel Spielraum bleibt?

Fuenf Bestandteile, gewichtet (model_config.STRUCTURE_WEIGHTS), alles FRED:
  curve     T10Y2Y    Zinskurve 10 J minus 2 J, woechentlich. Hoeher = normaler. Un-Inversions-Regel:
                      Versteilung nach einer Inversion ist das Krisensignal und deckelt den Kurven-Score.
  real      DFII10    Realzins 10 J, woechentlich, invertiert.
  cpi       CPILFESL  Kerninflation, Jahresrate, monatlich, invertiert.
  dsr       TDSP      Schuldendienstquote der Haushalte, quartalsweise, invertiert.
  interest  A091RC1Q027SBEA / W006RC1Q027SBEA  Zinslast des Bundes zu Steuereinnahmen, quartalsweise, invertiert.
Dazu das Regime-Flag Fiskalische Dominanz aus Zinslast, T-Bill-Anteil (Treasury) und Realzins-Repression.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Sequence
from datetime import datetime, timezone

from .. import fred, treasury
from ..fred import Observation
from ..model_config import (FISCAL_FLAG, PUBLICATION_LAG_DAYS, STRUCTURE_MONTHLY, STRUCTURE_QUARTERLY,
                            STRUCTURE_WEEKLY, STRUCTURE_WEIGHTS, UNINVERSION)
from ..schemas import Component, Headline, PillarResponse, Point, RegimeCriterion, RegimeFlag, ScoreBreakdown
from ..scoring import ScorePoint, invert_point, score_history, score_series, tone_for
from ..services import compute_change, ratio_series, resample_weekly, shift_dates, year_over_year
from .common import average_points, cached, weighted_breakdown

NAME = "Struktur & Fiskus"
MEASURES = "Wie viel Spielraum Notenbank und Staat strukturell noch haben: Zinsen, Inflation, Schulden."
LEGEND = "Ray Dalio"
SERIES = ["T10Y2Y", "DFII10", "CPILFESL", "TDSP", "A091RC1Q027SBEA", "W006RC1Q027SBEA", "DGS10", "CPIAUCSL"]
ORDER = ["curve", "real", "cpi", "dsr", "interest"]
MAX_AGE = {"real": 21, "cpi": 60, "dsr": 130, "interest": 130}


def invert(b: ScoreBreakdown) -> ScoreBreakdown:
    return b.model_copy(update={"score": 100 - b.score, "level": 100 - b.level, "momentum": 100 - b.momentum})


def aggregate(parts: dict[str, ScoreBreakdown]) -> ScoreBreakdown:
    return weighted_breakdown(parts, STRUCTURE_WEIGHTS, "weighted-component-scores")


def uninversion_flags(curve: Sequence[Observation]) -> list[bool]:
    """Je Woche: war die Kurve zuletzt invers und versteilt sie sich jetzt kraeftig?"""
    lb, sw, rise = UNINVERSION["lookback_weeks"], UNINVERSION["steepening_weeks"], UNINVERSION["min_rise_pp"]
    vals = [o.value for o in curve]
    return [
        i >= sw and min(vals[max(0, i - lb):i + 1]) < 0 and vals[i] - vals[i - sw] > rise
        for i in range(len(vals))
    ]


def apply_uninversion(points: list[ScorePoint], curve: Sequence[Observation]) -> list[ScorePoint]:
    flags = dict(zip((o.date for o in curve), uninversion_flags(curve)))
    cap = UNINVERSION["cap"]
    return [ScorePoint(p.date, min(p.score, cap), p.level, p.momentum, p.change) if flags.get(p.date) else p for p in points]


async def _data() -> dict:
    results = await asyncio.gather(*(fred.fetch_series(s) for s in SERIES), treasury.fetch_tbill_share())
    raw = {sid: res for sid, (res, _) in zip(SERIES, results[:-1])}
    tbill = results[-1][0]
    lag = PUBLICATION_LAG_DAYS
    series = {
        "curve": resample_weekly(raw["T10Y2Y"].observations),
        "real": resample_weekly(raw["DFII10"].observations),
        "cpi": shift_dates(year_over_year(raw["CPILFESL"].observations), lag["cpi"]),
        "dsr": shift_dates(raw["TDSP"].observations, lag["dsr"]),
        "interest": shift_dates(ratio_series(raw["A091RC1Q027SBEA"].observations, raw["W006RC1Q027SBEA"].observations), lag["bea_quarterly"]),
    }
    if any(len(v) < 12 for v in series.values()):
        raise fred.FredError("Zu wenig Daten fuer Struktur & Fiskus.")
    headline_cpi = year_over_year(raw["CPIAUCSL"].observations)
    return {"series": series, "raw": raw, "tbill": tbill, "dgs10": raw["DGS10"].observations, "headline_cpi": headline_cpi}


PARAMS = {"curve": STRUCTURE_WEEKLY, "real": STRUCTURE_WEEKLY, "cpi": STRUCTURE_MONTHLY, "dsr": STRUCTURE_QUARTERLY, "interest": STRUCTURE_QUARTERLY}
INVERTED = {"real", "cpi", "dsr", "interest"}


async def history() -> list[ScorePoint]:
    d = await _data()
    key = tuple(r.fetched_at for r in d["raw"].values()) + (d["tbill"].fetched_at,)

    def compute() -> list[ScorePoint]:
        hist = {k: score_history(d["series"][k], **PARAMS[k].history_kwargs()) for k in ORDER}
        hist = {k: ([invert_point(p) for p in v] if k in INVERTED else v) for k, v in hist.items()}
        hist["curve"] = apply_uninversion(hist["curve"], d["series"]["curve"])
        return average_points(hist["curve"], [hist[k] for k in ORDER[1:]],
                              max_age_days=[MAX_AGE[k] for k in ORDER[1:]], weights=[STRUCTURE_WEIGHTS[k] for k in ORDER])

    return cached("structure", key, compute)


def fiscal_regime(interest_pct: float, tbill_pct: float, repression_pp: float) -> RegimeFlag:
    f = FISCAL_FLAG
    criteria = [
        RegimeCriterion(label="Zinslast des Bundes zu Steuereinnahmen", value_text=f"{interest_pct:.0f} % (Schwelle {f['interest_tax_pct']:.0f} %)", met=interest_pct > f["interest_tax_pct"]),
        RegimeCriterion(label="T-Bill-Anteil an den Staatsschulden", value_text=f"{tbill_pct:.1f} % (Schwelle {f['tbill_share_pct']:.0f} %)", met=tbill_pct > f["tbill_share_pct"]),
        RegimeCriterion(label="Realzins-Repression (10 J minus Inflation)", value_text=f"{repression_pp:+.1f} Pp. (unter {f['repression_pp']:.0f})", met=repression_pp < f["repression_pp"]),
    ]
    met = sum(c.met for c in criteria)
    return RegimeFlag(
        id="fiscal_dominance", label="Fiskalische Dominanz", active=met >= f["needed"], met_count=met, needed=f["needed"],
        criteria=criteria,
        # Bis 18.09.2026 stand hier "Historisch profitieren Sachwerte und Gold". Der eigene Vergleich im
        # Profi-Modus misst fuer Gold eine Trennschaerfe von +0,03 und fuer Anleihen -0,05, also praktisch
        # nichts. Eine Behauptung, die die eigenen Daten widerlegen, gehoert nicht ins Werkzeug.
        hint="Der Staat finanziert sich kurz und teuer; die Notenbank kann die Zinsen kaum frei setzen. Was daraus für einzelne Anlageklassen folgt, misst dieses Modell nicht: Für Gold und Anleihen hat es kaum Aussagekraft.",
    )


LABELS = {
    "curve": "Zinskurve 10 J minus 2 J", "real": "Realzins 10 J (TIPS)", "cpi": "Kerninflation (Jahresrate)",
    "dsr": "Schuldendienst der Haushalte", "interest": "Zinslast des Bundes zu Steuern",
}
NOTES = {
    "curve": "Rendite zehnjähriger minus zweijähriger US-Staatsanleihen. Invers ging fast jeder Rezession voraus; die Versteilung danach ist das akute Signal.",
    "real": "Zins nach Abzug der erwarteten Inflation. Je höher, desto teurer wird Kapital für Firmen und Staat.",
    "cpi": "Verbraucherpreise ohne Energie und Lebensmittel. Ziel der Fed sind 2 Prozent; darüber hat sie weniger Spielraum.",
    "dsr": "Anteil des verfügbaren Einkommens, den US-Haushalte für Zins und Tilgung aufbringen. Steigt er, bricht der Konsum weg.",
    "interest": "Zinsausgaben des Bundes im Verhältnis zu den Steuereinnahmen. Über 25 Prozent gilt die Fiskalpolitik als handlungsunfähig.",
}
LAG_OF = {"cpi": PUBLICATION_LAG_DAYS["cpi"], "dsr": PUBLICATION_LAG_DAYS["dsr"], "interest": PUBLICATION_LAG_DAYS["bea_quarterly"]}


async def build(history_len: int = 1300) -> PillarResponse:
    from datetime import timedelta

    d = await _data()
    series = d["series"]
    parts: dict[str, ScoreBreakdown] = {}
    for k in ORDER:
        b = score_series([o.value for o in series[k]], **PARAMS[k].series_kwargs())
        if b:
            parts[k] = invert(b) if k in INVERTED else b
    curve = series["curve"]
    uninverting = uninversion_flags(curve)[-1]
    if uninverting and "curve" in parts:
        parts["curve"] = parts["curve"].model_copy(update={"score": min(parts["curve"].score, UNINVERSION["cap"])})
    total = aggregate(parts) if parts else None
    score = total.score if total else None

    components: list[Component] = []
    for k in ORDER:
        obs = series[k]
        ch = compute_change(obs, 13)
        components.append(Component(
            id=k, label=LABELS[k], value=obs[-1].value, unit="%", format="pp" if k == "curve" else "percent",  # type: ignore[arg-type]
            date=obs[-1].date - timedelta(days=LAG_OF.get(k, 0)), sign="+" if k == "curve" else "-",
            change_13w_abs=ch.abs if ch else None, score=parts[k].score if k in parts else None, note=NOTES[k],
        ))

    tbill_pct = d["tbill"].observations[-1].value
    repression = d["dgs10"][-1].value - d["headline_cpi"][-1].value
    regime = fiscal_regime(series["interest"][-1].value, tbill_pct, repression)

    latest = curve[-1]
    fingerprint = hashlib.sha1(
        f"structure:{latest.date}:{latest.value:.3f}:{score}:{regime.met_count}:{':'.join(f'{series[k][-1].value:.3f}' for k in ORDER)}".encode()
    ).hexdigest()[:12]
    weights_text = ", ".join(f"{LABELS[k].split(' ')[0]} {parts[k].score} ({STRUCTURE_WEIGHTS[k]:.0%})" for k in ORDER if k in parts)
    score_note = f"Gewichtet: {weights_text}. Alles außer der Kurve zählt invertiert."
    if uninverting:
        score_note += " Achtung: Versteilung nach Inversion, Kurven-Score gedeckelt."

    return PillarResponse(
        id="structure", name=NAME, measures=MEASURES, legend=LEGEND, status="live", frequency="weekly",
        tone=tone_for(score), score=total, score_note=score_note,
        headline=Headline(label="Zinskurve 10 J minus 2 J", value=latest.value, unit="Prozentpunkte", format="pp", date=latest.date),
        change_1w=compute_change(curve, 1), change_13w=compute_change(curve, 13), change_52w=compute_change(curve, 52),
        components=components, regime=regime,
        history=[Point(date=o.date, value=o.value) for o in curve[-history_len:]],
        source=d["raw"]["T10Y2Y"].source,
        fetched_at=datetime.fromtimestamp(max(r.fetched_at for r in d["raw"].values()), tz=timezone.utc),
        fingerprint=fingerprint,
    )
