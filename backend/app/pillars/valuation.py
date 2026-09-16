"""Overlay Bewertung & Fallhoehe: Wie tief geht es, wenn etwas schiefgeht?

Bewertung sagt auf Monate wenig ueber die Richtung, aber viel ueber die Fallhoehe. Deshalb kein Treiber,
sondern Overlay: 80 % Niveau ueber 30 Jahre, kleines Momentum. Drei Bestandteile (model_config):
  cape     Shiller CAPE (Kurs zu inflationsbereinigtem 10-Jahres-Gewinn), invertiert
  ecy      Excess CAPE Yield = Gewinnrendite minus Realzins, die Risikopraemie, nicht invertiert
  buffett  Marktwert aller US-Aktien (Fed Z.1, NCBEILQ027S) zu BIP, invertiert
Regime-Flag Extreme Bewertung: zwei von drei: CAPE im obersten Zehntel, Praemie unter 1 %, Buffett im obersten Zehntel.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import date, datetime, timedelta, timezone

from .. import fred, shiller
from ..fred import Observation
from ..model_config import (PUBLICATION_LAG_DAYS, VALUATION_FLAG, VALUATION_LABELS, VALUATION_MONTHLY,
                            VALUATION_MONTHLY_ABS, VALUATION_QUARTERLY, VALUATION_WEIGHTS)
from ..schemas import Component, Headline, PillarResponse, Point, RegimeCriterion, RegimeFlag, ScoreBreakdown
from ..scoring import ScorePoint, invert_point, percentile_rank, score_history, score_series, tone_for
from ..services import compute_change, ratio_series, shift_dates
from .common import average_points, cached, weighted_breakdown

NAME = "Bewertung"
MEASURES = "Wie teuer der Markt ist und wie groß die Fallhöhe bei Enttäuschungen: Sicherheitsmarge statt Timing."
LEGEND = "Shiller & Buffett"
ORDER = ["cape", "ecy", "buffett"]
PARAMS = {"cape": VALUATION_MONTHLY, "ecy": VALUATION_MONTHLY_ABS, "buffett": VALUATION_QUARTERLY}
INVERTED = {"cape", "buffett"}
LABELS = {
    "cape": "Shiller CAPE: Kurs zu 10-Jahres-Gewinn",
    "ecy": "Risikoprämie: Gewinnrendite minus Realzins",
    "buffett": "Buffett-Indikator: Aktien zu Wirtschaftsleistung",
}
NOTES = {
    "cape": "Kurs geteilt durch den inflationsbereinigten Durchschnittsgewinn der letzten zehn Jahre. Über 32 galt im Dokument als Blasenzone.",
    "ecy": "Was Aktien nach Abzug des sicheren Realzinses mehr abwerfen. Unter 1 Prozent preist der Markt Perfektion ein.",
    "buffett": "Marktwert aller US-Aktien im Verhältnis zur Jahreswirtschaftsleistung. Warren Buffetts Lieblingsmaß für Überhitzung.",
}
LAG = {"cape": PUBLICATION_LAG_DAYS["shiller"], "ecy": PUBLICATION_LAG_DAYS["shiller"], "buffett": PUBLICATION_LAG_DAYS["z1_quarterly"]}


def buffett_series(equities: list[Observation], gdp: list[Observation]) -> list[Observation]:
    """NCBEILQ027S in Mio. USD, GDP in Mrd. USD -> Prozent der Wirtschaftsleistung."""
    return ratio_series(equities, [Observation(date=o.date, value=o.value * 1000.0) for o in gdp], scale=100.0)


def fallhoehe_label(score: int | None) -> str:
    if score is None:
        return "unbekannt"
    return next(label for threshold, label in VALUATION_LABELS if score >= threshold)


async def _data() -> dict:
    # Z.1 und BIP ab 1975, damit das 30-Jahres-Fenster des Buffett-Indikators schon 2005 voll ist.
    (sh, _), (eq, _), (gdp, _) = await asyncio.gather(
        shiller.fetch_shiller(), fred.fetch_series("NCBEILQ027S", start=date(1975, 1, 1)), fred.fetch_series("GDP", start=date(1975, 1, 1))
    )
    series = {
        "cape": shift_dates(sh.cape, LAG["cape"]),
        "ecy": shift_dates(sh.ecy, LAG["ecy"]),
        "buffett": shift_dates(buffett_series(eq.observations, gdp.observations), LAG["buffett"]),
    }
    if any(len(v) < 60 for v in series.values()):
        raise shiller.ShillerError("Zu wenig Daten fuer die Bewertung.")
    key = (sh.fetched_at, eq.fetched_at, gdp.fetched_at)
    return {"series": series, "key": key, "fetched_at": max(key), "source": sh.source}


async def history() -> list[ScorePoint]:
    d = await _data()

    def compute() -> list[ScorePoint]:
        today = date.today()
        hist = {k: score_history(d["series"][k], **PARAMS[k].history_kwargs()) for k in ORDER}
        # Der laufende Shiller-Monat liegt nach dem Verzug in der Zukunft: erst ab Veroeffentlichung zaehlen.
        hist = {k: [p for p in v if p.date <= today] for k, v in hist.items()}
        hist = {k: ([invert_point(p) for p in v] if k in INVERTED else v) for k, v in hist.items()}
        return average_points(hist["cape"], [hist["ecy"], hist["buffett"]], max_age_days=[45, 200],
                              weights=[VALUATION_WEIGHTS[k] for k in ORDER])

    return cached("valuation", d["key"], compute)


def extreme_flag(cape: list[Observation], ecy: float, buffett: list[Observation]) -> RegimeFlag:
    f = VALUATION_FLAG
    cape_w = [o.value for o in cape[-VALUATION_MONTHLY.lookback:]]
    buf_w = [o.value for o in buffett[-VALUATION_QUARTERLY.lookback:]]
    cape_pct = percentile_rank(cape_w[:-1], cape_w[-1])
    buf_pct = percentile_rank(buf_w[:-1], buf_w[-1])
    criteria = [
        RegimeCriterion(label="CAPE im 30-Jahres-Vergleich", value_text=f"{cape_pct:.0f}. Perzentil (ab {f['cape_percentile']}.)", met=cape_pct >= f["cape_percentile"]),
        RegimeCriterion(label="Risikoprämie", value_text=f"{ecy:.2f} % (unter {f['ecy_min_pct']:.0f} %)", met=ecy < f["ecy_min_pct"]),
        RegimeCriterion(label="Buffett-Indikator im 30-Jahres-Vergleich", value_text=f"{buf_pct:.0f}. Perzentil (ab {f['buffett_percentile']}.)", met=buf_pct >= f["buffett_percentile"]),
    ]
    met = sum(c.met for c in criteria)
    return RegimeFlag(
        id="extreme_valuation", label="Extreme Bewertung", active=met >= f["needed"], met_count=met, needed=f["needed"], criteria=criteria,
        hint="Der Markt preist Perfektion ein. Schon kleine Enttäuschungen bei Liquidität oder Wachstum werden überproportional bestraft; die Fallhöhe ist maximal.",
    )


async def build(history_len: int = 360) -> PillarResponse:
    d = await _data()
    series = d["series"]
    parts: dict[str, ScoreBreakdown] = {}
    for k in ORDER:
        b = score_series([o.value for o in series[k]], **PARAMS[k].series_kwargs())
        if b:
            parts[k] = b.model_copy(update={"score": 100 - b.score, "level": 100 - b.level, "momentum": 100 - b.momentum}) if k in INVERTED else b
    total = weighted_breakdown(parts, VALUATION_WEIGHTS, "weighted-signal-scores") if parts else None
    score = total.score if total else None
    label = fallhoehe_label(score)

    components = []
    for k in ORDER:
        obs = series[k]
        ch = compute_change(obs, 13)
        components.append(Component(
            id=k, label=LABELS[k], value=obs[-1].value, unit="x" if k == "cape" else "%", format="index" if k == "cape" else "percent",  # type: ignore[arg-type]
            date=obs[-1].date - timedelta(days=LAG[k]), sign="+" if k == "ecy" else "-",
            change_13w_abs=ch.abs if ch else None, score=parts[k].score if k in parts else None, note=NOTES[k],
        ))
    regime = extreme_flag(series["cape"], series["ecy"][-1].value, series["buffett"])
    cape = series["cape"]
    latest = cape[-1]
    fingerprint = hashlib.sha1(f"valuation:{latest.date}:{latest.value:.2f}:{series['ecy'][-1].value:.3f}:{score}".encode()).hexdigest()[:12]
    parts_text = ", ".join(f"{LABELS[k].split(':')[0]} {parts[k].score} ({VALUATION_WEIGHTS[k]:.0%})" for k in ORDER if k in parts)
    score_note = f"Fallhöhe: {label}. Gewichtet: {parts_text}. CAPE und Buffett zählen invertiert."

    return PillarResponse(
        id="valuation", kind="overlay", name=NAME, measures=MEASURES, legend=LEGEND, status="live", frequency="monthly",
        tone=tone_for(score), score=total, score_note=score_note,
        headline=Headline(label="Shiller CAPE", value=latest.value, unit="x", format="index", date=latest.date - timedelta(days=LAG["cape"]), sign="-"),
        change_13w=compute_change(cape, 13), change_52w=compute_change(cape, 52),
        components=components, regime=regime,
        history=[Point(date=o.date - timedelta(days=LAG["cape"]), value=o.value) for o in cape[-history_len:]],
        source=d["source"], fetched_at=datetime.fromtimestamp(d["fetched_at"], tz=timezone.utc), fingerprint=fingerprint,
    )
