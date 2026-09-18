"""Was das Modell ueber sich selbst sagt: Version, Parameter, Konzentration, Vergleichsmassstab.

Hintergrund (Kritik vom 18.09.2026, Stufe D): Das Dashboard nennt drei Treiber und drei Overlays und wirkt
dadurch breiter, als es ist. Tatsaechlich bestimmt eine einzige Zeitreihe gut ein Viertel des Gesamtscores.
Wer das nicht weiss, haelt das Modell fuer diversifizierter als es ist. Dazu kommen zwei Angaben, die ein
Aussenstehender braucht, um die Zahlen einzuordnen: Der Rang misst gegen ein wanderndes Zehn-Jahres-Fenster,
und welche Parameter gerade gelten, stand bisher nur in der Git-Historie.
"""

from __future__ import annotations

import hashlib
import json

from .model_config import (
    CONSENSUS_WEIGHTS, LIQUIDITY_WEIGHTS, MECHANICS_RANGE, RANK_MIN_HISTORY, RANK_WINDOW_WEEKS,
    STRUCTURE_WEIGHTS, VALUATION_CAP, ZONE_BANDS, ZONE_CONFIRM_WEEKS,
)

METHOD = "macropilot-v2-rank"

# Alltagsnamen der Einzelserien. Die Konjunktur hat nur einen Bestandteil und geht deshalb voll ein.
SERIES_LABELS = {
    ("liquidity", "net"): "Net Liquidity der Fed",
    ("liquidity", "global"): "Notenbankbilanzen weltweit",
    ("liquidity", "tbill"): "Anteil kurzlaufender Staatsschulden",
    ("cycle", "composite"): "Regional-Fed-Umfragen",
    ("structure", "curve"): "Zinskurve",
    ("structure", "real"): "Realzins",
    ("structure", "cpi"): "Kerninflation",
    ("structure", "dsr"): "Schuldenlast der Haushalte",
    ("structure", "interest"): "Zinslast des Staates",
}
PILLAR_LABELS = {"liquidity": "Liquidität", "cycle": "Konjunktur", "structure": "Struktur & Fiskus"}
INNER_WEIGHTS: dict[str, dict[str, float]] = {
    "liquidity": LIQUIDITY_WEIGHTS,
    "cycle": {"composite": 1.0},
    "structure": STRUCTURE_WEIGHTS,
}


def concentration() -> list[dict]:
    """Anteil jeder Einzelserie am Gesamtscore, absteigend. Gewicht der Saeule mal Gewicht im Inneren."""
    rows = [
        {
            "pillar": pillar, "pillar_label": PILLAR_LABELS.get(pillar, pillar),
            "label": SERIES_LABELS.get((pillar, key), key),
            "share": round(CONSENSUS_WEIGHTS[pillar] * inner, 4),
        }
        for pillar, weights in INNER_WEIGHTS.items()
        for key, inner in weights.items()
        if pillar in CONSENSUS_WEIGHTS
    ]
    return sorted(rows, key=lambda r: r["share"], reverse=True)


def parameters_hash() -> str:
    """Kurzer Fingerabdruck der wirksamen Parameter, damit eine Zahl spaeter zuordenbar bleibt."""
    payload = json.dumps({
        "consensus": CONSENSUS_WEIGHTS, "liquidity": LIQUIDITY_WEIGHTS, "structure": STRUCTURE_WEIGHTS,
        "mechanics_range": MECHANICS_RANGE, "valuation_cap": VALUATION_CAP,
        "rank_window": RANK_WINDOW_WEEKS, "zone_bands": ZONE_BANDS, "zone_confirm": ZONE_CONFIRM_WEEKS,
    }, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:10]


# Handgepflegtes Protokoll der Modellaenderungen. Ohne das steht die Parameterkennung ohne Datum da, und
# der Leser kann nicht wissen, ab wann welche Zahlen galten. Neueste Aenderung zuerst.
MODEL_CHANGES = [
    {"date": "2026-09-18", "what": "Treibergewichte von 55/15/30 auf 40/15/45",
     "why": "Die Konzentration auf die Liquiditaet war durch die Daten nicht gedeckt"},
    {"date": "2026-09-16", "what": "Marktsignale vom Treiber zum Overlay",
     "why": "Als Treiber verschlechterten sie den Score, als Bestaetigung sind sie aussagekraeftig"},
    {"date": "2026-09-16", "what": "Anzeige auf Rang mit Ampelzonen umgestellt",
     "why": "Der Rohwert war komprimiert und trennte kaum"},
]


def model_card() -> dict:
    top = concentration()
    central_bank = sum(r["share"] for r in top if r["label"].startswith(("Net Liquidity", "Notenbankbilanzen")))
    return {
        "version": METHOD,
        "parameters_hash": parameters_hash(),
        "weights": dict(CONSENSUS_WEIGHTS),
        "rank_window_weeks": RANK_WINDOW_WEEKS,
        "rank_min_history_weeks": RANK_MIN_HISTORY,
        "zone_confirm_weeks": ZONE_CONFIRM_WEEKS,
        "concentration": top,
        "central_bank_share": round(central_bank, 4),
        "changes": MODEL_CHANGES,
        #: Die Historie wird bei jedem Lauf mit den heutigen Parametern nachgerechnet. Der Verlauf zeigt also
        #: nicht, was das Werkzeug damals angezeigt hat. Ab dem ersten Tagesbild gilt das nicht mehr.
        "history_recomputed": True,
    }
