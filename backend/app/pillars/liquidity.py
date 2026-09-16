"""Saeule 1 - Liquiditaet (Denkschule Michael Howell): Wie viel Geld fliesst ins System?

Drei gewichtete Signale (model_config.LIQUIDITY_WEIGHTS):
  net     Net Liquidity = Fed-Bilanz (WALCL) - Staatskonto TGA (WTREGEN) - Reverse Repo (RRPONTSYD), Mio. USD
  global  Notenbank-Proxy fuer Howells Global Liquidity: Fed + EZB (ECBASSETSW, Mio. EUR) + BoJ (JPNASSETS,
          100 Mio. JPY), in USD umgerechnet mit Wochenkursen EURUSD und USDJPY
  tbill   T-Bill-Anteil an den marktfaehigen Staatsschulden (Treasury): steigt er, ziehen Geldmarktfonds
          Mittel aus der Reverse-Repo-Fazilitaet und der Fiskus spuelt Liquiditaet in den Markt
"""

from __future__ import annotations

import asyncio
import hashlib
from bisect import bisect_right
from collections.abc import Sequence
from datetime import date, datetime, timezone

from .. import fred, market, treasury
from ..fred import Observation, SeriesResult
from ..model_config import LIQUIDITY, LIQUIDITY_GLOBAL, LIQUIDITY_TBILL, LIQUIDITY_WEIGHTS, PUBLICATION_LAG_DAYS
from ..schemas import Component, Headline, PillarResponse, Point, ScoreBreakdown
from ..scoring import ScorePoint, score_history, score_series, tone_for
from ..services import compute_change, shift_dates
from .common import average_points, cached, weighted_breakdown

NAME = "Liquidität"
MEASURES = "Wie viel Geld die Notenbanken und der Fiskus dem Finanzsystem netto zur Verfügung stellen."
LEGEND = "Michael Howell"

SERIES = {"walcl": "WALCL", "tga": "WTREGEN", "rrp": "RRPONTSYD", "ecb": "ECBASSETSW", "boj": "JPNASSETS"}
FX = {"eurusd": "EURUSD=X", "usdjpy": "JPY=X"}
RRP_TO_MILLIONS = 1000.0
BOJ_TO_MILLIONS_JPY = 100.0
PARAMS = {"net": LIQUIDITY, "global": LIQUIDITY_GLOBAL, "tbill": LIQUIDITY_TBILL}


def _last_on_or_before(obs: Sequence[Observation], d: date, max_age_days: int) -> float | None:
    dates = [o.date for o in obs]
    i = bisect_right(dates, d) - 1
    if i < 0 or (d - dates[i]).days > max_age_days:
        return None
    return obs[i].value


def compute_net_liquidity(walcl: Sequence[Observation], tga: Sequence[Observation], rrp: Sequence[Observation]) -> list[Observation]:
    """Richtet TGA (woechentlich) und RRP (taeglich) auf die WALCL-Wochen aus.
    Vor 2013 gab es Reverse Repo nur sporadisch und in winzigen Volumen: fehlende Werte zaehlen als 0."""
    out: list[Observation] = []
    for o in walcl:
        t = _last_on_or_before(tga, o.date, 14)
        if t is None:
            continue
        r = _last_on_or_before(rrp, o.date, 400) or 0.0
        out.append(Observation(date=o.date, value=o.value - t - r * RRP_TO_MILLIONS))
    return out


def compute_global_liquidity(
    walcl: Sequence[Observation], ecb: Sequence[Observation], boj: Sequence[Observation],
    eurusd: Sequence[Observation], usdjpy: Sequence[Observation],
) -> list[Observation]:
    """Fed + EZB + BoJ in Mio. USD je WALCL-Woche; fehlt ein Teil oder ist er zu alt, entfaellt die Woche."""
    out: list[Observation] = []
    for o in walcl:
        e, j = _last_on_or_before(ecb, o.date, 14), _last_on_or_before(boj, o.date, 62)
        fx_eur, fx_jpy = _last_on_or_before(eurusd, o.date, 14), _last_on_or_before(usdjpy, o.date, 14)
        if None in (e, j, fx_eur, fx_jpy) or not fx_jpy:
            continue
        out.append(Observation(date=o.date, value=o.value + e * fx_eur + j * BOJ_TO_MILLIONS_JPY / fx_jpy))  # type: ignore[operator]
    return out


async def _data() -> dict:
    fred_results, prices, (tbill, _) = await asyncio.gather(
        asyncio.gather(*(fred.fetch_series(s) for s in SERIES.values())),
        market.fetch_many(list(FX.values())),
        treasury.fetch_tbill_share(),
    )
    raw: dict[str, SeriesResult] = {k: res for k, (res, _) in zip(SERIES, fred_results)}
    net = compute_net_liquidity(raw["walcl"].observations, raw["tga"].observations, raw["rrp"].observations)
    if not net:
        raise fred.FredError("Net Liquidity konnte nicht berechnet werden: keine ueberlappenden Daten.")
    glob = compute_global_liquidity(
        raw["walcl"].observations, raw["ecb"].observations, raw["boj"].observations,
        prices[FX["eurusd"]].observations, prices[FX["usdjpy"]].observations,
    )
    series = {"net": net, "global": glob, "tbill": tbill.observations}
    # Fuer den Verlauf (C3): BoJ-Bilanz und Schuldenstand erst ab Veroeffentlichung sichtbar. Live nutzt die
    # juengsten veroeffentlichten Werte, die Termine bleiben dort unverschoben.
    glob_hist = compute_global_liquidity(
        raw["walcl"].observations, raw["ecb"].observations, shift_dates(raw["boj"].observations, PUBLICATION_LAG_DAYS["boj"]),
        prices[FX["eurusd"]].observations, prices[FX["usdjpy"]].observations,
    )
    history_series = {"net": net, "global": glob_hist, "tbill": shift_dates(tbill.observations, PUBLICATION_LAG_DAYS["mspd"])}
    key = tuple(r.fetched_at for r in raw.values()) + tuple(p.fetched_at for p in prices.values()) + (tbill.fetched_at,)
    return {"series": series, "history_series": history_series, "raw": raw, "key": key, "fetched_at": max(r.fetched_at for r in raw.values())}


async def history() -> list[ScorePoint]:
    """Gewichtetes Mittel der drei Signale je Woche; Basis-Termine sind die von Net Liquidity."""
    d = await _data()

    def compute() -> list[ScorePoint]:
        hist = {k: score_history(d["history_series"][k], **PARAMS[k].history_kwargs()) for k in PARAMS}
        return average_points(hist["net"], [hist["global"], hist["tbill"]], max_age_days=[21, 62],
                              weights=[LIQUIDITY_WEIGHTS[k] for k in ("net", "global", "tbill")])

    return cached("liquidity", d["key"], compute)


SIGNAL_LABELS = {
    "net": "Net Liquidity: Fed minus TGA minus Reverse Repo",
    "global": "Notenbanken global: Fed + EZB + BoJ in Dollar",
    "tbill": "T-Bill-Anteil an den Staatsschulden",
}
SIGNAL_NOTES = {
    "net": "Das Geld, das dem US-Finanzsystem nach Abzug von Staatskonto und Reverse Repo tatsächlich zur Verfügung steht.",
    "global": "Die drei großen Bilanzen zusammen, in Dollar. Kapital kennt keine Grenzen, deshalb zählt die Summe.",
    "tbill": "Anteil kurzlaufender Schatzwechsel. Steigt er, ziehen Geldmarktfonds Mittel von der Fed ab und der Fiskus schafft Liquidität.",
}


def _part(cid: str, label: str, res: SeriesResult, *, sign: str, scale: float, note: str) -> Component:
    obs = res.observations
    ch = compute_change(obs, LIQUIDITY.momentum_window)
    return Component(
        id=cid, label=label, value=obs[-1].value * scale, unit="Mio. USD", format="usd_millions", date=obs[-1].date,
        sign=sign, change_13w_pct=round(ch.pct, 3) if ch else None, change_13w_abs=ch.abs * scale if ch else None, note=note,  # type: ignore[arg-type]
    )


async def build(history_len: int = 1300) -> PillarResponse:
    d = await _data()
    series, raw = d["series"], d["raw"]
    parts: dict[str, ScoreBreakdown] = {}
    for k in PARAMS:
        b = score_series([o.value for o in series[k]], **PARAMS[k].series_kwargs())
        if b:
            parts[k] = b
    total = weighted_breakdown(parts, LIQUIDITY_WEIGHTS, "weighted-signal-scores") if parts else None
    score = total.score if total else None

    components: list[Component] = []
    for k in ("net", "global", "tbill"):
        obs = series[k]
        ch = compute_change(obs, PARAMS[k].momentum_window)  # Veraenderung ueber das Momentum-Fenster des Signals
        is_pct = k == "tbill"
        components.append(Component(
            id=k, label=SIGNAL_LABELS[k], value=obs[-1].value, unit="%" if is_pct else "Mio. USD",
            format="percent" if is_pct else "usd_millions", date=obs[-1].date, sign="+",  # type: ignore[arg-type]
            change_13w_pct=None if is_pct or not ch else round(ch.pct, 3), change_13w_abs=ch.abs if ch else None,
            score=parts[k].score if k in parts else None, note=SIGNAL_NOTES[k],
        ))
    components += [
        _part("walcl", "Fed-Bilanz", raw["walcl"], sign="+", scale=1.0, note="Alles, was die Fed an Anleihen und Krediten hält. Wächst sie, kommt Geld ins System."),
        _part("tga", "Staatskonto (TGA)", raw["tga"], sign="-", scale=1.0, note="Das Girokonto des US-Finanzministeriums bei der Fed. Geld darauf ist dem Markt entzogen."),
        _part("rrp", "Reverse Repo", raw["rrp"], sign="-", scale=RRP_TO_MILLIONS, note="Geld, das Fonds über Nacht bei der Fed parken statt es zu investieren."),
    ]

    net = series["net"]
    latest = net[-1]
    fingerprint = hashlib.sha1(f"liquidity:{latest.date}:{latest.value:.0f}:{score}:{series['global'][-1].value:.0f}:{series['tbill'][-1].value:.2f}".encode()).hexdigest()[:12]
    weights_text = ", ".join(f"{SIGNAL_LABELS[k].split(':')[0]} {parts[k].score} ({LIQUIDITY_WEIGHTS[k]:.0%})" for k in PARAMS if k in parts)
    score_note = f"Gewichtet: {weights_text}." if parts else "Zu wenig Historie für einen Score."

    return PillarResponse(
        id="liquidity", name=NAME, measures=MEASURES, legend=LEGEND, status="live", frequency="weekly",
        tone=tone_for(score), score=total, score_note=score_note,
        headline=Headline(label="Net Liquidity", value=latest.value, unit="Mio. USD", format="usd_millions", date=latest.date),
        change_1w=compute_change(net, 1), change_13w=compute_change(net, LIQUIDITY.momentum_window), change_52w=compute_change(net, 52),
        components=components,
        history=[Point(date=o.date, value=o.value) for o in net[-history_len:]],
        source=raw["walcl"].source,
        fetched_at=datetime.fromtimestamp(d["fetched_at"], tz=timezone.utc),
        fingerprint=fingerprint,
    )
