"""Easy-Modus: je Baustein ein Wort und drei kurze Saetze in Alltagssprache.

Bis 17.09.2026 stand hier ein Satz aus zwei Bausteinen ("Der Geldzufluss ist ausgeglichen. Der Trend ist
unauffaellig."). Das beschrieb den Zustand, sagte aber nicht, woran er gerade liegt und was die Saeule fuer den
Gesamtscore ueberhaupt bedeutet. Seitdem entstehen drei getrennte Zeilen:

  easy_summary  Lage und Richtung, mit ausgesprochenem Zeitraum.
  easy_drivers  Welcher Bestandteil die Saeule gerade traegt und welcher sie bremst, in Alltagsworten.
  easy_role     Was die Saeule im Gesamtscore bewirkt: Gewicht bei den Treibern, Aufgabe bei den Overlays.

Grundsatz: keine Fachbegriffe, keine Perzentile, hoechstens eine Zahl pro Satz.
"""

from __future__ import annotations

from .model_config import CONSENSUS_WEIGHTS
from .pillars.valuation import fallhoehe_label
from .schemas import Component, PillarResponse

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

# Alltagsnamen der Bestandteile. Die technischen Labels stehen weiter im Profi-Modus.
PART_NAMES: dict[str, dict[str, str]] = {
    "liquidity": {
        "net": "das Geld, das die US-Notenbank netto im System lässt",
        "global": "die Bilanzen der großen Notenbanken zusammen",
        "tbill": "der Anteil kurzlaufender Staatsschulden",
    },
    "cycle": {"phi": "rund um Philadelphia", "ny": "rund um New York", "dal": "in Texas"},
    "structure": {
        "curve": "die Zinskurve",
        "real": "der Zins nach Abzug der Inflation",
        "cpi": "die Kerninflation",
        "dsr": "die Schuldenlast der Haushalte",
        "interest": "die Zinslast des Staates",
    },
    "markets": {
        "breadth": "die Breite der Kursgewinne",
        "risk": "die Risikofreude am Devisenmarkt",
        "real": "das Verhältnis von Kupfer zu Gold",
        "credit": "der Markt für riskante Unternehmensanleihen",
    },
    "mechanics": {
        "vix": "die erwartete Schwankung der nächsten Wochen",
        "term": "das Verhältnis von kurzfristigem zu längerfristigem Stress",
        "skew": "der Preis einer Versicherung gegen einen Absturz",
    },
    "valuation": {
        "cape": "der Preis gemessen an zehn Jahren Gewinn",
        "ecy": "der Vorsprung von Aktien gegenüber Anleihen",
        "buffett": "der Börsenwert gemessen an der Wirtschaftsleistung",
    },
}

# Je Baustein ein passender Satzrahmen. {high} ist der beste, {low} der schwaechste Bestandteil.
PART_FRAME = {
    "liquidity": "Am meisten Schub gibt gerade {high}, am wenigsten {low}.",
    "cycle": "Am besten läuft es {high}, am schwächsten {low}.",
    "structure": "Den meisten Spielraum gibt {high}, den geringsten {low}.",
    "markets": "Am stärksten stützt gerade {high}, am schwächsten {low}.",
    "mechanics": "Am ruhigsten ist {high}, am angespanntesten {low}.",
    "valuation": "Noch am günstigsten ist {high}, am teuersten {low}.",
}

DRIVER_ROLE_EXTRA = {
    "liquidity": " Damit wiegt sie schwerer als alle anderen.",
    "cycle": " Damit wiegt sie am wenigsten, weil sie kurzfristig wenig über die Kurse sagt.",
    "structure": "",
}

# Das Gewicht als Zahl zu nennen, war eine Falle: Bei der Liquiditaet stand "55 von 100 Punkten" direkt unter
# dem Score 55, rein zufaellig dieselbe Zahl. Ein Anteil in Worten kann damit nicht verwechselt werden.
WEIGHT_WORDS = [
    (0.62, "mehr als drei Fünftel"), (0.52, "gut die Hälfte"), (0.45, "etwa die Hälfte"),
    (0.36, "gut ein Drittel"), (0.28, "knapp ein Drittel"), (0.22, "ein knappes Viertel"),
    (0.17, "ein knappes Fünftel"), (0.12, "etwa ein Siebtel"), (0.0, "einen kleinen Teil"),
]


def weight_words(weight: float) -> str:
    return next(words for threshold, words in WEIGHT_WORDS if weight >= threshold)
OVERLAY_ROLE = {
    "valuation": "Zählt nicht in den Gesamtscore. Sie begrenzt ihn nach oben: Je teurer der Markt, desto tiefer der Deckel.",
    "mechanics": "Zählt nicht in den Gesamtscore. Sie verschiebt ihn um wenige Punkte gegen die Stimmung, weil Panik historisch eher eine Kaufzone war.",
    "markets": "Zählt nicht in den Gesamtscore. Sie sagt nur, ob der Markt das Makrobild bestätigt.",
}


def _span_words(weeks: int, unit: str) -> str:
    """Fenster in Alltagssprache. 26 Wochen sind 'ein halbes Jahr', nicht '26 Wochen'."""
    months = weeks if unit == "months" else max(1, round(weeks / 4.33))
    return {1: "einem Monat", 3: "drei Monaten", 6: "einem halben Jahr", 12: "einem Jahr"}.get(months, f"{months} Monaten")


TREND_WEEKS = 13
TREND_SPAN = "drei Monaten"


def _direction(score_change: int | None, momentum: int, span: str) -> str:
    """Richtung des Scores ueber die letzten Wochen, in Alltagsworten.

    Frueher stand hier das Momentum-Perzentil. Das beschreibt das Tempo der zugrunde liegenden Kennzahl, nicht
    die Veraenderung des Scores, den der Leser sieht. Ergebnis war ein falscher Satz: Der Struktur-Score stieg
    in dreizehn Wochen von 29 auf 40, waehrend daneben "hat sich daran wenig geaendert" stand. Ohne Historie
    bleibt das Momentum als Rueckfall, dann aber als Aussage ueber das Tempo.
    """
    if score_change is None:
        if momentum >= 58:
            return f"Das Tempo ist zuletzt hoch, über {span} gerechnet."
        if momentum > 42:
            return f"Das Tempo ist über {span} unauffällig."
        return f"Das Tempo ist zuletzt schwach, über {span} gerechnet."
    if score_change >= 10:
        return f"In {TREND_SPAN} um {score_change} Punkte gestiegen."
    if score_change >= 4:
        return f"In {TREND_SPAN} leicht gestiegen, um {score_change} Punkte."
    if score_change > -4:
        return f"In {TREND_SPAN} kaum verändert."
    if score_change > -10:
        return f"In {TREND_SPAN} leicht gefallen, um {abs(score_change)} Punkte."
    return f"In {TREND_SPAN} um {abs(score_change)} Punkte gefallen."


def _ranked(p: PillarResponse) -> list[tuple[Component, float]]:
    """Bestandteile mit einer vergleichbaren Zahl: Teil-Score, sonst der Rohwert (Konjunktur-Umfragen)."""
    scored = [(c, float(c.score)) for c in p.components if c.score is not None]
    if scored:
        return sorted(scored, key=lambda x: x[1])
    named = PART_NAMES.get(p.id, {})
    return sorted(((c, c.value) for c in p.components if c.id in named), key=lambda x: x[1])


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


def easy_summary(p: PillarResponse, score_change: int | None = None) -> str:
    """Lage und Richtung. Der Zeitraum wird ausgesprochen, damit 'Trend' nicht in der Luft haengt."""
    if p.score is None:
        return "Noch kein Score verfügbar."
    direction = _direction(score_change, p.score.momentum, _span_words(p.score.momentum_window, p.score.unit))
    if p.id == "valuation":
        return f"{VALUATION_INTRO.get(easy_label(p), 'Bewertung ohne Einordnung.')} {direction}"
    if p.id == "mechanics":
        intro = {
            "Panik-Zone": "Panik am Markt, historisch eher Kaufzone als Verkaufszeitpunkt.",
            "ruhig": "Die Markttechnik ist ruhig, Rückschläge werden gekauft.",
            "angespannt": "Die Markttechnik ist angespannt, Rückschläge können sich verstärken.",
        }.get(easy_label(p), "Die Markttechnik ist unauffällig.")
        return f"{intro} {direction}"
    if p.id == "markets" and p.regime and p.regime.active:
        return f"{p.regime.hint} {direction}"
    return f"{DRIVER_INTRO.get(p.id, {}).get(p.tone, '')} {direction}".strip()


def easy_drivers(p: PillarResponse) -> str:
    """Woran die Saeule gerade haengt: staerkster und schwaechster Bestandteil mit Alltagsnamen.

    Liegen alle Bestandteile dicht beieinander, waere das Herausgreifen von Extremen irrefuehrend. Dann sagt
    der Satz genau das.
    """
    names = PART_NAMES.get(p.id, {})
    ranked = [(c, v) for c, v in _ranked(p) if c.id in names]
    if len(ranked) < 2:
        return ""
    (low, low_v), (high, high_v) = ranked[0], ranked[-1]
    if high_v - low_v < 15:
        return "Die Bestandteile liegen dicht beieinander, keiner sticht heraus."
    frame = PART_FRAME.get(p.id, "Am stärksten wirkt gerade {high}, am schwächsten {low}.")
    return frame.format(high=names[high.id], low=names[low.id])


def easy_role(p: PillarResponse) -> str:
    """Was die Saeule fuer den Gesamtscore tut. Ohne diesen Satz bleibt unklar, warum die Kachel da ist."""
    if p.kind == "overlay":
        return OVERLAY_ROLE.get(p.id, "")
    weight = CONSENSUS_WEIGHTS.get(p.id)
    if weight is None:
        return ""
    return f"Macht {weight_words(weight)} des Gesamtscores aus.{DRIVER_ROLE_EXTRA.get(p.id, '')}"


def annotate(p: PillarResponse, score_change: int | None = None) -> PillarResponse:
    return p.model_copy(update={
        "easy_label": easy_label(p), "easy_summary": easy_summary(p, score_change),
        "easy_drivers": easy_drivers(p), "easy_role": easy_role(p),
    })
