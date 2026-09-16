"""Gemeinsame Bausteine aller Erklaerungs-Provider: Prompt, Faktenaufbereitung, SSL."""

from __future__ import annotations

import json
import ssl
from dataclasses import dataclass

from ..schemas import Change, PillarResponse

try:
    import truststore
except ImportError:  # pragma: no cover
    truststore = None

SYSTEM_PROMPT = """Du schreibst für MacroPilot, ein Dashboard, das Hobby-Investoren die Wirtschaftslage erklärt.
Du bekommst die aktuellen Daten einer Säule als JSON und erklärst in einfachen Worten, warum der Score so ist, wie er ist.

So schreibst du:
- Deutsch, ein Absatz, drei bis vier kurze Sätze. Keine Aufzählung, keine Überschrift, kein Markdown.
- Erkläre wie einem klugen Freund ohne Finanzausbildung. Fachbegriffe vermeiden oder in einem Halbsatz erklären.
- Nenne die wichtigsten Zahlen aus den Daten, gerundet, zum Beispiel "5,9 Billionen Dollar" oder "plus 0,2 Prozent in 13 Wochen".
- Reihenfolge: Erst, was die Hauptkennzahl gerade bedeutet. Dann, warum der Score so hoch oder niedrig ausfällt. Dann, was ihn zuletzt nach oben oder unten bewegt hat.
- Die Score-Skala: 0 ist maximal Risk-Off (Winter), 100 ist maximal Risk-On (Sommer). Der Score kombiniert das Niveau (Perzentil über zehn Jahre) mit dem Momentum (Richtung der letzten Wochen bis Monate, je nach Säule).
- Übernimm die Felder "einordnung" und "wirkung" wörtlich als Richtung. Rechne keine Richtungen selbst aus und erfinde keine Bewegung, die nicht in den Daten steht.
- Keine Anlageempfehlung. Keine Wörter wie kaufen, verkaufen, halten, sollte man.
- Steig direkt mit dem Inhalt ein, keine Einleitung, keine Floskeln, keine Warnhinweise."""


@dataclass
class GenResult:
    """Ergebnis eines Providers. text=None bedeutet Fehler, error erklaert warum."""

    text: str | None
    model: str
    error: str | None = None


def ssl_context() -> ssl.SSLContext | bool:
    """Zertifikatspeicher des Betriebssystems nutzen (auf Windows noetig)."""
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT) if truststore else True


def _money(millions: float) -> str:
    if abs(millions) >= 1_000_000:
        return f"{millions / 1_000_000:.2f} Billionen USD"
    return f"{millions / 1_000:.0f} Milliarden USD"


def _fmt(value: float, fmt: str) -> str | float:
    return _money(value) if fmt == "usd_millions" else round(value, 3)


UNITS = {"index": "Punkte", "diffusion": "Punkte", "percent": "Prozentpunkte", "pp": "Prozentpunkte"}


def _change(ch: Change | None, fmt: str) -> dict | None:
    """Prozentangaben nur bei Geld und Verhaeltnissen; bei Punkten und Prozentpunkten ist die
    prozentuale Veraenderung irrefuehrend (z. B. Zinskurve von 0,27 auf 0,42 = +55 %)."""
    if ch is None:
        return None
    if fmt in UNITS:
        return {"absolut": f"{ch.abs:+.2f} {UNITS[fmt]}", "wochen": ch.weeks}
    return {"absolut": _fmt(ch.abs, fmt), "prozent": round(ch.pct, 2), "wochen": ch.weeks}


def facts_for_prompt(p: PillarResponse) -> dict:
    """Kompakte, gerundete Fakten fuer das Modell. Keine Rohdaten-Listen."""
    fmt = p.headline.format
    return {
        "saeule": p.name,
        "misst": p.measures,
        "denkschule": p.legend,
        "datenfrequenz": p.frequency,
        "score": p.score.model_dump() if p.score else None,
        "score_hinweis": p.score_note,
        "tendenz": p.tone,
        "hauptkennzahl": {
            "label": p.headline.label,
            "wert": _fmt(p.headline.value, fmt),
            "einheit": p.headline.unit,
            "stand": p.headline.date.isoformat(),
        },
        "veraenderung": {
            "1_woche": _change(p.change_1w, fmt),
            "13_wochen": _change(p.change_13w, fmt),
            "52_wochen": _change(p.change_52w, fmt),
        },
        "einordnung": _judgments(p),
        "bestandteile": [_component_facts(p, c) for c in p.components],
        "regime": (
            {
                "label": p.regime.label, "aktiv": p.regime.active,
                "kriterien_erfuellt": f"{p.regime.met_count} von {p.regime.needed}",
                "kriterien": [{"label": c.label, "wert": c.value_text, "erfuellt": c.met} for c in p.regime.criteria],
                "bedeutung": p.regime.hint,
            }
            if p.regime else None
        ),
    }


def _judgments(p: PillarResponse) -> dict:
    """Vorgerechnete Einordnung, damit kleine Modelle keine Richtungen erfinden."""
    from . import template  # lokaler Import, template haengt von base ab

    out: dict = {"groesster_treiber": template.driver_sentence(p) or None}
    if p.score:
        s = p.score
        out["niveau"] = "hoch" if s.level >= 70 else "niedrig" if s.level <= 30 else "unauffaellig"
        out["momentum"] = "kraeftig" if s.momentum >= 70 else "schwach" if s.momentum <= 30 else "unauffaellig"
    if p.change_13w:
        out["richtung_zuletzt"] = "gestiegen" if p.change_13w.abs >= 0 else "gefallen"
    return out


def _component_facts(p: PillarResponse, c) -> dict:
    delta = c.change_13w_abs
    wirkung = None
    if delta is not None:
        rising = delta >= 0
        helps = (rising and c.sign == "+") or (not rising and c.sign == "-")
        richtung = "gestiegen" if rising else "gefallen"
        if p.id == "liquidity":
            effekt = "bringt Geld ins System" if helps else "entzieht dem Markt Geld"
        elif p.id == "structure":
            effekt = "schafft Spielraum" if helps else "engt den Spielraum ein"
        else:
            effekt = "stuetzt die Kennzahl" if helps else "belastet die Kennzahl"
        wirkung = f"{richtung}, {effekt}"
    return {
        "label": c.label,
        "wert": _fmt(c.value, c.format),
        "einheit": c.unit,
        "geht_ein_als": "plus" if c.sign == "+" else "minus",
        "veraenderung_13_wochen_absolut": _fmt(delta, c.format) if delta is not None else None,
        "wirkung": wirkung,
        "teilscore": c.score,
        "hinweis": c.note,
    }


def user_message(p: PillarResponse) -> str:
    return json.dumps(facts_for_prompt(p), ensure_ascii=False, indent=2)
