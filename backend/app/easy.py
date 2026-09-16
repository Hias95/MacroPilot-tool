"""Easy-Modus: je Baustein ein Wort und ein Satz, ohne Zahlen ausser dem Score.

Das Label folgt dem Score (Treiber: Gegenwind / Neutral / Rueckenwind; Bewertung: Fallhoehe-Stufe;
Marktmechanik: ruhig / unauffaellig / angespannt / Panik-Zone; Marktsignale: Risiko gesucht / gemischt /
Rueckzug / Marktstress / Kapitulation). Der Satz kombiniert Lage und Trend.
"""

from __future__ import annotations

from .pillars.valuation import fallhoehe_label
from .schemas import PillarResponse

TONE_LABEL = {"bearish": "Gegenwind", "neutral": "Neutral", "bullish": "Rückenwind"}

DRIVER_INTRO = {
    "liquidity": {"bullish": "Es kommt netto Geld ins System.", "neutral": "Der Geldzufluss ist ausgeglichen.", "bearish": "Dem System wird netto Geld entzogen."},
    "cycle": {"bullish": "Die Industrie beschleunigt.", "neutral": "Die Industrie tritt auf der Stelle.", "bearish": "Die Industrie bremst."},
    "markets": {"bullish": "Das Geld an den Märkten sucht Risiko.", "neutral": "Die Marktsignale sind gemischt.", "bearish": "Das Geld zieht sich zurück."},
    "structure": {"bullish": "Notenbank und Staat haben Spielraum.", "neutral": "Der Spielraum ist begrenzt.", "bearish": "Der Spielraum ist eng."},
}
VALUATION_INTRO = {
    "günstig": "Der Markt ist günstig, viel Sicherheitspuffer.",
    "fair": "Der Markt ist fair bewertet.",
    "teuer": "Der Markt ist teuer, die Fallhöhe ist hoch.",
    "extrem teuer": "Der Markt ist extrem teuer, die Fallhöhe ist maximal.",
}


def easy_label(p: PillarResponse) -> str:
    score = p.score.score if p.score else None
    if p.id == "valuation":
        return fallhoehe_label(score)
    if p.id == "mechanics":
        if p.regime and p.regime.active:
            return "Panik-Zone"
        if score is None:
            return "unbekannt"
        return "ruhig" if score > 60 else "angespannt" if score < 40 else "unauffällig"
    if p.id == "markets":
        if p.regime and p.regime.active:
            return p.regime.label
        return {"bullish": "Risiko gesucht", "neutral": "gemischt", "bearish": "Rückzug"}[p.tone]
    return TONE_LABEL[p.tone]


def easy_summary(p: PillarResponse) -> str:
    if p.score is None:
        return "Noch kein Score verfügbar."
    momentum = p.score.momentum
    trend = "Der Trend zeigt klar nach oben." if momentum >= 70 else "Der Trend zeigt nach unten." if momentum <= 30 else "Der Trend ist unauffällig."
    if p.id == "valuation":
        return VALUATION_INTRO.get(easy_label(p), "Bewertung ohne Einordnung.")
    if p.id == "mechanics":
        label = easy_label(p)
        intro = {
            "Panik-Zone": "Panik am Markt, historisch eher Kaufzone als Verkaufszeitpunkt.",
            "ruhig": "Die Markttechnik ist ruhig, Rückschläge werden gekauft.",
            "angespannt": "Die Markttechnik ist angespannt, Rückschläge können sich verstärken.",
        }.get(label, "Die Markttechnik ist unauffällig.")
        return intro
    if p.id == "markets" and p.regime and p.regime.active:
        return p.regime.hint
    intro = DRIVER_INTRO.get(p.id, {}).get(p.tone, "")
    return f"{intro} {trend}".strip()


def annotate(p: PillarResponse) -> PillarResponse:
    return p.model_copy(update={"easy_label": easy_label(p), "easy_summary": easy_summary(p)})
