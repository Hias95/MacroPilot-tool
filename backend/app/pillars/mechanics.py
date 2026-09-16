"""Overlay Marktmechanik & Volatilitaet: Wie verwundbar ist die Markttechnik gerade?

Dealer-Gamma, CTA-Positionierung und die BofA-Cashquote sind proprietaer. Kostenlose Proxys, die dieselbe
Mechanik abbilden (Volatilitaetskontrollfonds und Gamma-Hedging wirken ueber die Volatilitaet):
  vix   VIX-Niveau (CBOE), invertiert: hoch = Stress, erzwungene Verkaeufe systematischer Fonds
  term  Terminstruktur VIX / VIX3M (CBOE), invertiert: ueber 1 (Backwardation) = akuter Stress
  skew  CBOE SKEW (Yahoo ^SKEW), invertiert: hoch = teure Absicherung gegen Abstuerze
Kontra-Regel: Liegt das VIX-Niveau im obersten Zehntel der letzten zehn Jahre, gilt die Panik-Zone.
Historisch waren das eher Kauf- als Verkaufszeitpunkte; der Consensus (A7) nutzt das als Hinweis.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone

from .. import cboe, market
from ..fred import Observation
from ..model_config import MECHANICS_LEVEL, MECHANICS_RATIO, MECHANICS_WEIGHTS, PANIC_VIX_PERCENTILE
from ..schemas import Component, Headline, PillarResponse, Point, RegimeCriterion, RegimeFlag, ScoreBreakdown
from ..scoring import ScorePoint, invert_point, percentile_rank, score_history, score_series, tone_for
from ..services import compute_change, ratio_series, resample_weekly
from .common import average_points, cached, weighted_breakdown

NAME = "Marktmechanik"
MEASURES = "Wie angespannt die Markttechnik ist: Volatilität, Terminstruktur, Absicherungsnachfrage."
LEGEND = "Volatilitätskontrolle & Gamma"
ORDER = ["vix", "term", "skew"]
PARAMS = {"vix": MECHANICS_LEVEL, "term": MECHANICS_RATIO, "skew": MECHANICS_LEVEL}
LABELS = {"vix": "VIX: erwartete Schwankung 30 Tage", "term": "Terminstruktur: VIX zu VIX3M", "skew": "SKEW: Preis der Absturz-Absicherung"}
NOTES = {
    "vix": "Erwartete Schwankung des S&P 500 in den nächsten 30 Tagen. Steigt sie, müssen volatilitätsgesteuerte Fonds mechanisch verkaufen.",
    "term": "Kurzfristige Volatilität geteilt durch dreimonatige. Über 1 heißt: Der Markt fürchtet das Jetzt mehr als die Zukunft, ein Stresszeichen.",
    "skew": "Wie teuer Absicherung gegen einen Absturz relativ zu normalen Optionen ist. Hoch heißt: Große Adressen kaufen Schutz.",
}


async def _data() -> dict:
    (vix, _), (vix3m, _), prices = await asyncio.gather(
        cboe.fetch_index("VIX"), cboe.fetch_index("VIX3M"), market.fetch_many(["^SKEW"]),
    )
    vix_w = resample_weekly(vix.observations)
    term = ratio_series(vix_w, resample_weekly(vix3m.observations), scale=1.0)
    skew = prices["^SKEW"].observations
    if len(vix_w) < 120 or len(term) < 120 or len(skew) < 120:
        raise cboe.CboeError("Zu wenig Daten fuer die Marktmechanik.")
    key = (vix.fetched_at, vix3m.fetched_at, prices["^SKEW"].fetched_at)
    return {"series": {"vix": vix_w, "term": term, "skew": skew}, "key": key, "fetched_at": max(key), "source": vix.source}


async def history() -> list[ScorePoint]:
    d = await _data()

    def compute() -> list[ScorePoint]:
        hist = {k: [invert_point(p) for p in score_history(d["series"][k], **PARAMS[k].history_kwargs())] for k in ORDER}
        return average_points(hist["vix"], [hist["term"], hist["skew"]], max_age_days=[21, 21],
                              weights=[MECHANICS_WEIGHTS[k] for k in ORDER])

    return cached("mechanics", d["key"], compute)


def panic_flag(vix: list[Observation], term_ratio: float) -> RegimeFlag:
    window = [o.value for o in vix[-MECHANICS_LEVEL.lookback:]]
    pct = percentile_rank(window[:-1], window[-1])
    backwardation = term_ratio > 1.0
    return RegimeFlag(
        id="panic_zone", label="Panik-Zone", active=pct >= PANIC_VIX_PERCENTILE, met_count=int(pct >= PANIC_VIX_PERCENTILE), needed=1,
        criteria=[
            RegimeCriterion(label="VIX-Niveau im Zehn-Jahres-Vergleich", value_text=f"{pct:.0f}. Perzentil (ab {PANIC_VIX_PERCENTILE}.)", met=pct >= PANIC_VIX_PERCENTILE),
            RegimeCriterion(label="Terminstruktur in Backwardation", value_text=f"VIX/VIX3M {term_ratio:.2f} (über 1,00)", met=backwardation),
        ],
        hint="Extreme Angst war historisch eher Kauf- als Verkaufszeitpunkt. Wer in der Panik verkauft, verkauft meist zu spät.",
    )


async def build(history_len: int = 1300) -> PillarResponse:
    d = await _data()
    series = d["series"]
    parts: dict[str, ScoreBreakdown] = {}
    for k in ORDER:
        b = score_series([o.value for o in series[k]], **PARAMS[k].series_kwargs())
        if b:
            parts[k] = b.model_copy(update={"score": 100 - b.score, "level": 100 - b.level, "momentum": 100 - b.momentum})
    total = weighted_breakdown(parts, MECHANICS_WEIGHTS, "weighted-signal-scores") if parts else None
    score = total.score if total else None

    components = []
    for k in ORDER:
        obs = series[k]
        ch = compute_change(obs, 13)
        components.append(Component(
            id=k, label=LABELS[k], value=obs[-1].value, unit="Punkte" if k != "term" else "Verhältnis",
            format="ratio" if k == "term" else "index", date=obs[-1].date, sign="-",  # type: ignore[arg-type]
            change_13w_pct=round(ch.pct, 3) if ch and k == "term" else None, change_13w_abs=ch.abs if ch else None,
            score=parts[k].score if k in parts else None, note=NOTES[k],
        ))
    regime = panic_flag(series["vix"], series["term"][-1].value)
    vix = series["vix"]
    latest = vix[-1]
    fingerprint = hashlib.sha1(f"mechanics:{latest.date}:{latest.value:.2f}:{series['term'][-1].value:.3f}:{score}".encode()).hexdigest()[:12]
    parts_text = ", ".join(f"{LABELS[k].split(':')[0]} {parts[k].score} ({MECHANICS_WEIGHTS[k]:.0%})" for k in ORDER if k in parts)
    score_note = f"Gewichtet, alles invertiert: {parts_text}. Hoch = ruhige Technik, niedrig = Kaskadengefahr."

    return PillarResponse(
        id="mechanics", kind="overlay", name=NAME, measures=MEASURES, legend=LEGEND, status="live", frequency="weekly",
        tone=tone_for(score), score=total, score_note=score_note,
        headline=Headline(label="VIX", value=latest.value, unit="Punkte", format="index", date=latest.date, sign="-"),
        change_1w=compute_change(vix, 1), change_13w=compute_change(vix, 13), change_52w=compute_change(vix, 52),
        components=components, regime=regime,
        history=[Point(date=o.date, value=o.value) for o in vix[-history_len:]],
        source=d["source"], fetched_at=datetime.fromtimestamp(d["fetched_at"], tz=timezone.utc), fingerprint=fingerprint,
    )
