"""Consensus v2: gewichtete Treiber, Overlays als Korrektur und Deckel, Vetos, Rang mit Ampelzone, Zyklusphase.

Score (0 bis 100, Risk-Off bis Risk-On):
  1. Kern = gewichtetes Mittel der vier Treiber (CONSENSUS_WEIGHTS).
  2. Marktmechanik korrigiert um bis zu |MECHANICS_RANGE| Punkte. Seit C2 ist das Vorzeichen negativ (Kontra):
     Stress hebt den Rohwert leicht an, Sorglosigkeit senkt ihn, weil extreme Angst historisch eher Kaufzone war.
  3. Bewertung deckelt nach oben (Fallhoehe): Deckel = base + slope * Bewertungs-Score.
  4. Vetos deckeln bei Systemkrisen: Liquiditaet, Struktur, sowie extreme Bewertung plus gestresste Mechanik.
Angezeigt wird nicht der Rohwert, sondern sein Rang gegenueber den letzten RANK_WINDOW_WEEKS Wochen
("besser als X % der Wochen der letzten zehn Jahre"), weil der Rohwert komprimiert ist (Backtest C1).
Ampelzone: Quantil des Rangs (ZONE_BANDS), in der Historie erst nach ZONE_CONFIRM_WEEKS Wochen bestaetigt.
Zyklusphase: Richtung Liquiditaet x Konjunktur, bestaetigt nach PHASE_CONFIRM_WEEKS Wochen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .model_config import (
    CONSENSUS_WEIGHTS, MARKET_CONFIRM_THRESHOLD, MECHANICS_RANGE, PHASE_MATRIX, VALUATION_CAP, VETOES,
    ZONE_BANDS, ZONE_CONFIRM_WEEKS,
)
from .schemas import ConsensusResponse, PillarResponse
from .scoring import percentile_rank

PHASE_LABEL = {key: label for key, label in PHASE_MATRIX.values()}
VETO_LABEL = {
    "liquidity": "Liquiditätskrise",
    "structure": "Strukturkrise",
    "valuation_mechanics": "Extreme Bewertung bei gestresster Markttechnik",
}


@dataclass(frozen=True)
class Snapshot:
    score: int
    momentum: int
    change: float | None  # Vorzeichen bestimmt die Richtung


@dataclass(frozen=True)
class Overlay:
    score: int | None
    regime_active: bool = False


@dataclass(frozen=True)
class CoreResult:
    score: int
    core: float
    adjusted: float
    cap: float | None
    valuation_cap: float | None
    mechanics_adjustment: float
    vetoes: list[str]
    phase_raw_key: str
    liquidity_direction: str
    growth_direction: str
    confidence: str
    contributions: dict[str, float] = field(default_factory=dict)


ZONE_LABEL = {key: label for _, key, label in ZONE_BANDS}


@dataclass(frozen=True)
class ConsensusParams:
    """Kalibrierbare Parameter des Kerns; Standard = model_config. markets_sign -1 nutzt Marktsignale invers."""

    weights: dict[str, float] = field(default_factory=lambda: dict(CONSENSUS_WEIGHTS))
    mechanics_range: float = MECHANICS_RANGE
    valuation_cap: dict[str, float] = field(default_factory=lambda: dict(VALUATION_CAP))
    vetoes: dict[str, float] = field(default_factory=lambda: dict(VETOES))
    markets_sign: int = 1


DEFAULT_PARAMS = ConsensusParams()


def zone_for(rank: float | None) -> tuple[str, str]:
    r = 50.0 if rank is None else rank
    for upper, key, label in ZONE_BANDS:
        if r < upper:
            return key, label
    return ZONE_BANDS[-1][1], ZONE_BANDS[-1][2]


def _direction(s: Snapshot) -> str:
    if s.change is not None:
        return "up" if s.change >= 0 else "down"
    return "up" if s.momentum >= 50 else "down"


# Die Zyklusphase braucht eine binaere Richtung, der Text nicht. Eine Veraenderung von +0,85 % ueber 26 Wochen
# ist "up", historisch aber unauffaellig (Momentum im 53. Perzentil). Stand frueher "Liquiditaet steigt",
# waehrend die Saeule daneben "wenig geaendert" sagte. Dieselben Schwellen wie in easy.py.
DIRECTION_WORDS = [
    (75, "legt deutlich zu", "steigt deutlich"),
    (58, "legt leicht zu", "steigt leicht"),
    (42, "verändert sich kaum", "kaum verändert"),
    (25, "gibt leicht nach", "fällt leicht"),
    (0, "gibt deutlich nach", "fällt deutlich"),
]


def direction_words(momentum: int) -> tuple[str, str]:
    """Satzform und Kurzform derselben Abstufung, damit Badge und Fliesstext nie auseinanderlaufen."""
    for threshold, sentence, short in DIRECTION_WORDS:
        if momentum >= threshold:
            return sentence, short
    return DIRECTION_WORDS[-1][1], DIRECTION_WORDS[-1][2]


def _clamp(x: float) -> int:
    return int(min(100, max(0, round(x))))


def core(drivers: dict[str, Snapshot], valuation: Overlay | None = None, mechanics: Overlay | None = None,
         params: ConsensusParams = DEFAULT_PARAMS) -> CoreResult:
    """Die Rechnung ohne Text. Wird fuer den Live-Wert, jede Woche der Historie und die Kalibrierung genutzt."""
    W, VT = params.weights, params.vetoes
    total_w = sum(W.values())

    def value_of(k: str) -> float:
        v = drivers[k].score
        return 100 - v if k == "markets" and params.markets_sign < 0 else v

    contributions = {k: W[k] * value_of(k) / total_w for k in W}
    core_value = sum(contributions.values())

    mech_adj = 0.0
    if mechanics and mechanics.score is not None:
        mech_adj = (mechanics.score - 50) / 50 * params.mechanics_range
        if mechanics.regime_active and mech_adj < 0:
            mech_adj = 0.0
    adjusted = core_value + mech_adj

    caps: list[float] = []
    val_cap = None
    if valuation and valuation.score is not None:
        val_cap = params.valuation_cap["base"] + params.valuation_cap["slope"] * valuation.score
        caps.append(val_cap)
    vetoes: list[str] = []
    if drivers["liquidity"].score < VT["liquidity_below"]:
        vetoes.append("liquidity"); caps.append(VT["liquidity_cap"])
    if drivers["structure"].score < VT["structure_below"]:
        vetoes.append("structure"); caps.append(VT["structure_cap"])
    mech_stressed = bool(mechanics and mechanics.score is not None and mechanics.score < VT["mechanics_below"] and not mechanics.regime_active)
    if valuation and valuation.regime_active and mech_stressed:
        vetoes.append("valuation_mechanics"); caps.append(VT["valuation_mechanics_cap"])
    cap = min(caps) if caps else None
    final = _clamp(min(adjusted, cap) if cap is not None else adjusted)

    liq_dir, growth_dir = _direction(drivers["liquidity"]), _direction(drivers["cycle"])
    phase_key, _ = PHASE_MATRIX[(liq_dir, growth_dir)]
    confidence = "knapp" if min(abs(drivers["liquidity"].momentum - 50), abs(drivers["cycle"].momentum - 50)) < 10 else "klar"
    return CoreResult(
        score=final, core=core_value, adjusted=adjusted, cap=cap, valuation_cap=val_cap, mechanics_adjustment=mech_adj,
        vetoes=vetoes, phase_raw_key=phase_key,
        liquidity_direction=liq_dir, growth_direction=growth_dir, confidence=confidence, contributions=contributions,
    )


def snapshot_of(p: PillarResponse) -> Snapshot:
    """Richtung aus der Veraenderung ueber das Momentum-Fenster der Saeule, wie im Verlauf; Fallback 13 Wochen."""
    change = p.score.change if p.score and p.score.change is not None else (p.change_13w.abs if p.change_13w else None)
    return Snapshot(score=p.score.score if p.score else 50, momentum=p.score.momentum if p.score else 50, change=change)


def overlay_of(p: PillarResponse | None) -> Overlay | None:
    if p is None:
        return None
    return Overlay(score=p.score.score if p.score else None, regime_active=bool(p.regime and p.regime.active))


@dataclass(frozen=True)
class ConsensusState:
    """Was der Live-Consensus aus der Historie braucht: Rang-Fenster, bestaetigte Zone und Phase."""

    window: list[float]
    zone_key: str
    weeks_in_zone: int
    phase_key: str
    weeks_in_phase: int
    # Zone, die aktuell auf Bestaetigung wartet, und wie viele Wochen in Folge sie schon anliegt.
    zone_pending_key: str | None = None
    zone_pending_weeks: int = 0
    #: Letzter Rastertag der Historie, Bezugspunkt fuer das Datum der Bestaetigung.
    last_date: date | None = None


DRIVER_NAMES = {"liquidity": "Liquidität", "cycle": "Konjunktur", "structure": "Struktur & Fiskus"}
MARKET_CONFIRM_LABEL = {"confirmed": "Markt bestätigt", "market_ahead": "Markt läuft voraus", "market_lagging": "Markt zögert"}


def market_confirmation(rank: int | None, markets_score: int | None) -> str | None:
    """Bestaetigt der Marktsignal-Score den Consensus-Rang? Beide ueber oder beide unter der Schwelle = bestaetigt.
    Markt hoch bei Rang tief = Markt laeuft voraus (historisch schwaechste Kombination), Rang hoch bei Markt tief =
    Markt zoegert (gleiche Rendite, mehr Rueckschlaege)."""
    if rank is None or markets_score is None:
        return None
    t = MARKET_CONFIRM_THRESHOLD
    if (rank >= t) == (markets_score >= t):
        return "confirmed"
    return "market_ahead" if markets_score >= t else "market_lagging"


def _fallback(scores: dict[str, int | None], overlay_scores: dict[str, int | None]) -> ConsensusResponse:
    available = [s for s in scores.values() if s is not None]
    score = round(sum(available) / len(available)) if available else None
    key, label = zone_for(score)
    return ConsensusResponse(
        score=score, composite=score, zone_key=key, zone=label, method="mean-fallback",  # type: ignore[arg-type]
        note="Mittelwert, weil nicht alle Treiber einen Score liefern.", why="Für die volle Logik fehlen Treiber-Scores.",
        pillar_scores=scores, overlay_scores=overlay_scores, confidence="knapp",
    )


def _why(r: CoreResult, by: dict[str, PillarResponse], ov: dict[str, PillarResponse], phase_key: str, weeks: int | None,
         rank: int, zone: str, zone_raw: str, weeks_in_zone: int | None,
         pending_weeks: int = 0, change_date: date | None = None) -> str:
    from .pillars.valuation import fallhoehe_label

    strongest = max(DRIVER_NAMES, key=lambda k: by[k].score.score if by[k].score else 0)
    weakest = min(DRIVER_NAMES, key=lambda k: by[k].score.score if by[k].score else 0)
    first = f"{zone}: Die Lage ist besser als in {rank} Prozent der Wochen der letzten zehn Jahre (Rohwert {r.score})"
    first += f", seit {weeks_in_zone} Wochen in dieser Zone." if weeks_in_zone else "."
    if zone_raw != zone:
        # Aus dem Widerspruch zwischen Nadel und Wort wird eine Vorschau mit Datum.
        first += f" Diese Woche zeigt bereits {zone_raw}"
        if pending_weeks >= 2:  # "die 1. Woche in Folge" waere umstaendlich
            first += f", die {pending_weeks}. Woche in Folge"
        if change_date:
            first += f"; bestätigt wäre der Wechsel am {change_date.strftime('%d.%m.%Y')}, wenn es so bleibt."
        else:
            first += ", noch unbestätigt."
    parts = [
        first,
        f"Am stärksten stützt {DRIVER_NAMES[strongest]} ({by[strongest].score.score}), "
        f"am meisten bremst {DRIVER_NAMES[weakest]} ({by[weakest].score.score}).",  # type: ignore[union-attr]
    ]
    growth = direction_words(by["cycle"].score.momentum)[0] if by.get("cycle") and by["cycle"].score else "bewegt sich"
    liq = direction_words(by["liquidity"].score.momentum)[0] if by.get("liquidity") and by["liquidity"].score else "bewegt sich"
    since = f", seit {weeks} Wochen" if weeks else ""
    phase_text = f"Zyklusphase {PHASE_LABEL[phase_key]}{since}: die Konjunktur {growth}, die Liquidität {liq}."
    if phase_key != r.phase_raw_key:
        phase_text += f" Das Rohsignal zeigt bereits {PHASE_LABEL[r.phase_raw_key]}, noch unbestätigt."
    if r.confidence == "knapp":
        phase_text += " Die Einordnung ist knapp."
    parts.append(phase_text)

    val = ov.get("valuation")
    if val and val.score and r.valuation_cap is not None:
        text = f"Bewertung {fallhoehe_label(val.score.score)} (Score {val.score.score}): Deckel bei {r.valuation_cap:.0f}."
        if r.cap is not None and r.adjusted > r.cap and abs(r.cap - r.valuation_cap) < 0.5:
            text += f" Der Deckel greift und drückt den Wert von {r.adjusted:.0f} auf {r.score}."
        else:
            # Ein Deckel, der nicht greift, ist keine Bremse. Vorher blieb das offen und las sich wie eine.
            text += f" Er greift derzeit nicht, der Rohwert liegt mit {r.adjusted:.0f} darunter."
        parts.append(text)
    mech = ov.get("mechanics")
    if mech and mech.score:
        adj = "±0" if abs(r.mechanics_adjustment) < 0.5 else f"{r.mechanics_adjustment:+.0f}"
        if mech.regime and mech.regime.active:
            parts.append(f"Marktmechanik in der Panik-Zone ({adj} Punkte): extreme Angst war historisch eher Kaufzone.")
        else:
            mood = "ruhig" if mech.score.score > 60 else "angespannt" if mech.score.score < 40 else "unauffällig"
            reason = " Sorglosigkeit kostet etwas Rohwert." if r.mechanics_adjustment <= -1 else " Stress zählt als Kontra-Signal leicht positiv." if r.mechanics_adjustment >= 1 else ""
            parts.append(f"Marktmechanik {mood} ({adj} Punkte).{reason}")
    mk = ov.get("markets")
    if mk and mk.score:
        key = market_confirmation(rank, mk.score.score)
        if mk.regime and mk.regime.active:
            parts.append(f"{mk.regime.label} (Marktsignale {mk.score.score}): {mk.regime.hint}")
        elif key == "market_ahead":
            parts.append(f"Der Markt läuft dem Makrobild voraus (Marktsignale {mk.score.score} bei Rang {rank}): historisch die schwächste Kombination.")
        elif key == "market_lagging":
            parts.append(f"Der Markt zögert noch (Marktsignale {mk.score.score} bei Rang {rank}): Rendite historisch gleich, Rückschläge häufiger.")
        elif key == "confirmed":
            parts.append(f"Der Markt bestätigt das Bild (Marktsignale {mk.score.score}).")
    if r.vetoes:
        parts.append(f"Veto aktiv: {', '.join(VETO_LABEL[v] for v in r.vetoes)}, Deckel bei {r.cap:.0f}.")
    else:
        parts.append("Kein Veto aktiv.")
    return " ".join(parts)


def build_consensus(
    pillars: list[PillarResponse], overlays: list[PillarResponse] | None = None, state: ConsensusState | None = None
) -> ConsensusResponse:
    by = {p.id: p for p in pillars}
    ov = {p.id: p for p in (overlays or [])}
    scores = {p.id: (p.score.score if p.score else None) for p in pillars}
    overlay_scores = {p.id: (p.score.score if p.score else None) for p in (overlays or [])}
    if any(k not in by or by[k].score is None for k in CONSENSUS_WEIGHTS):
        return _fallback(scores, overlay_scores)

    drivers = {k: snapshot_of(by[k]) for k in CONSENSUS_WEIGHTS}
    r = core(drivers, overlay_of(ov.get("valuation")), overlay_of(ov.get("mechanics")))
    rank = round(percentile_rank(state.window, r.score)) if state and state.window else r.score
    zone_raw_key, zone_raw = zone_for(rank)
    zone_key = state.zone_key if state else zone_raw_key
    zone = ZONE_LABEL[zone_key]
    weeks_in_zone = state.weeks_in_zone if state else None
    phase_key = state.phase_key if state else r.phase_raw_key
    weeks = state.weeks_in_phase if state else None
    # Schwebender Zonenwechsel: Wie viele Wochen liegt die abweichende Zone schon an, und wann waere sie
    # bestaetigt? Die Historie zaehlt den Lauf mit; stimmt der Live-Rohwert nicht mit ihrem Kandidaten
    # ueberein, beginnt der Lauf mit dieser Woche neu.
    pending_key = zone_raw_key if zone_raw_key != zone_key else None
    if pending_key is None:
        pending_weeks, change_date = 0, None
    else:
        same = state is not None and state.zone_pending_key == pending_key and state.zone_pending_weeks > 0
        pending_weeks = state.zone_pending_weeks if same and state else 1  # type: ignore[union-attr]
        remaining = max(0, ZONE_CONFIRM_WEEKS - pending_weeks)
        change_date = state.last_date + timedelta(weeks=remaining) if state and state.last_date else None
    mk = ov.get("markets")
    confirm_key = market_confirmation(rank, mk.score.score if mk and mk.score else None)
    return ConsensusResponse(
        score=rank, composite=r.score, zone_key=zone_key, zone=zone, zone_raw_key=zone_raw_key, weeks_in_zone=weeks_in_zone,  # type: ignore[arg-type]
        zone_pending_key=pending_key, zone_pending_weeks=pending_weeks, zone_confirm_weeks=ZONE_CONFIRM_WEEKS,  # type: ignore[arg-type]
        zone_change_date=change_date,
        market_confirmation_key=confirm_key, market_confirmation=MARKET_CONFIRM_LABEL.get(confirm_key) if confirm_key else None,  # type: ignore[arg-type]
        phase_key=phase_key, phase=PHASE_LABEL[phase_key], phase_raw_key=r.phase_raw_key, weeks_in_phase=weeks,  # type: ignore[arg-type]
        liquidity_direction=r.liquidity_direction, growth_direction=r.growth_direction, confidence=r.confidence,  # type: ignore[arg-type]
        liquidity_move=direction_words(by["liquidity"].score.momentum)[1] if by["liquidity"].score else None,
        growth_move=direction_words(by["cycle"].score.momentum)[1] if by["cycle"].score else None,
        method="macropilot-v2-rank",
        note="Rohwert aus drei gewichteten Treibern, Marktmechanik als Kontra-Korrektur, Bewertung als Deckel, Marktsignale als Bestätigung, Vetos bei Systemkrisen. Angezeigt wird der Rang des Rohwerts in den letzten zehn Jahren; Zone und Zyklusphase wechseln erst nach Bestätigung.",
        why=_why(r, by, ov, phase_key, weeks, rank, zone, zone_raw, weeks_in_zone, pending_weeks, change_date),
        pillar_scores=scores, overlay_scores=overlay_scores,
        core=round(r.core, 1), mechanics_adjustment=round(r.mechanics_adjustment, 1), valuation_cap=round(r.valuation_cap, 1) if r.valuation_cap is not None else None,
        vetoes=r.vetoes, cap=round(r.cap, 1) if r.cap is not None else None, adjusted=round(r.adjusted, 1),
        # Ein Deckel ueber dem Wert aendert nichts. Ohne diese Angabe wirkte "Bewertung extrem teuer, Deckel
        # bei 66" wie eine aktive Bremse, obwohl der Rohwert mit 56 klar darunter lag.
        cap_binding=r.cap is not None and r.adjusted > r.cap,
    )
