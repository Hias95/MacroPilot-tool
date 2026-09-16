"""Regelbasierte Erklaerung ohne KI. Immer verfuegbar, kostenlos, deterministisch.

Baut aus den Fakten drei bis vier einfache deutsche Saetze: Bedeutung der Hauptkennzahl,
Begruendung des Scores (Niveau und Momentum) und der groesste Treiber der letzten 13 Wochen.
"""

from __future__ import annotations

from datetime import date

from ..schemas import Change, PillarResponse
from .base import GenResult

MODEL_NAME = "regelbasiert"


def de_num(value: float, digits: int) -> str:
    text = f"{value:,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def de_money(millions: float) -> str:
    amount = abs(millions)
    if amount >= 1_000_000:
        return f"{de_num(amount / 1_000_000, 2)} Billionen Dollar"
    if amount >= 1_000:
        return f"{de_num(amount / 1_000, 0)} Milliarden Dollar"
    return f"{de_num(amount, 0)} Millionen Dollar"


def de_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _amount(ch: Change, fmt: str) -> str:
    if fmt == "usd_millions":
        return de_money(ch.abs)
    if fmt in ("index", "diffusion"):
        return f"{de_num(abs(ch.abs), 1)} Punkte"
    if fmt in ("percent", "pp"):
        return f"{de_num(abs(ch.abs), 2)} Prozentpunkte"
    return f"{de_num(abs(ch.pct), 1)} Prozent"


def meaning_sentence(p: PillarResponse) -> str:
    h = p.headline
    stand = f"Stand {de_date(h.date)}"
    v = h.value
    if p.id == "liquidity":
        return f"Netto stehen dem Finanzsystem aktuell {de_money(v)} an Liquidität zur Verfügung ({stand})."
    if p.id == "cycle":
        signed = f"{'+' if v >= 0 else '-'}{de_num(abs(v), 1)}"
        if v >= 0:
            return (
                f"Der Durchschnitt der regionalen Fed-Umfragen liegt bei {signed} Punkten, also über null: "
                f"Mehr Industriefirmen melden steigende als fallende Aktivität ({stand})."
            )
        return (
            f"Der Durchschnitt der regionalen Fed-Umfragen liegt bei {signed} Punkten, also unter null: "
            f"Mehr Industriefirmen melden fallende als steigende Aktivität ({stand})."
        )
    if p.id == "structure":
        shape = "normal" if v >= 0 else "invers, historisch ein Warnsignal"
        who = "Zehnjährige US-Anleihen bringen" if v >= 0 else "Zweijährige US-Anleihen bringen"
        other = "zweijährige" if v >= 0 else "zehnjährige"
        text = f"{who} {de_num(abs(v), 2)} Prozentpunkte mehr Zins als {other}, die Zinskurve ist also {shape}"
        extra = {c.id: c for c in p.components}
        if "cpi" in extra and "real" in extra:
            text += f". Die Kerninflation liegt bei {de_num(extra['cpi'].value, 1)} Prozent, der Realzins bei {de_num(extra['real'].value, 2)} Prozent"
        return f"{text} ({stand})."
    if p.id == "valuation":
        comps = {c.id: c for c in p.components}
        text = f"Der Shiller-CAPE, der Kurs im Verhältnis zum Zehn-Jahres-Gewinn, liegt bei {de_num(v, 1)}"
        if "ecy" in comps:
            text += f", die Risikoprämie gegenüber sicheren Anleihen bei {de_num(comps['ecy'].value, 2)} Prozent"
        if "buffett" in comps:
            text += f", der Buffett-Indikator bei {de_num(comps['buffett'].value, 0)} Prozent der Wirtschaftsleistung"
        return f"{text} ({stand})."
    if p.id == "mechanics":
        comps = {c.id: c for c in p.components}
        term = comps["term"].value if "term" in comps else None
        text = f"Der VIX, das Angstbarometer der Börse, steht bei {de_num(v, 1)} Punkten"
        if term is not None:
            text += (
                f", und die Terminstruktur liegt bei {de_num(term, 2)}: "
                + ("kurzfristige Absicherung ist teurer als langfristige, ein Stresszeichen" if term > 1.0
                   else "der Markt erwartet ruhigere Wochen als heute, die Technik ist entspannt")
            )
        return f"{text} ({stand})."
    if p.id == "markets" and p.components:
        def signal(c) -> str:
            pct = c.change_13w_pct or 0.0
            return f"{c.label.split(':')[0]} ({'+' if pct >= 0 else '-'}{de_num(abs(pct), 1)} Prozent)"
        ups = [c for c in p.components if (c.change_13w_pct or 0.0) > 0]
        downs = [c for c in p.components if (c.change_13w_pct or 0.0) <= 0]
        text = f"Von {len(p.components)} Markt-Signalen zeigen {len(ups)} in den letzten 13 Wochen nach oben"
        text += f": {', '.join(signal(c) for c in ups)}." if ups else "."
        if downs:
            text += f" Zurück bleiben {', '.join(signal(c) for c in downs)}."
        return f"{text} ({stand})"
    if h.format == "ratio":
        return f"{h.label} liegt bei {de_num(v, 3)} ({stand})."
    return f"{h.label} liegt bei {de_num(v, 2)} {h.unit} ({stand})."


def _span(p: PillarResponse) -> str:
    """Zeitraum der Kopf-Veraenderung; change_13w.weeks zaehlt in Wochen, auch bei Monatsdaten (13 Wochen = 3 Monate)."""
    n = p.change_13w.weeks if p.change_13w else None
    if p.frequency == "monthly":
        return f"{max(1, round(n / 4.33)) if n else 3} Monaten"
    return f"{n or 13} Wochen"


def score_sentences(p: PillarResponse) -> list[str]:
    if not p.score:
        return ["Für einen Score fehlt noch genug Historie."]
    s = p.score
    if s.level >= 70:
        level = f"Das Niveau ist hoch: höher als in {s.level} Prozent der letzten zehn Jahre."
    elif s.level <= 30:
        level = f"Das Niveau ist niedrig: nur in {s.level} Prozent der letzten zehn Jahre lag der Wert tiefer."
    else:
        level = f"Das Niveau ist unauffällig: höher als in {s.level} Prozent der letzten zehn Jahre."

    momentum = ""
    if p.change_13w:
        ch = p.change_13w
        direction = "gestiegen" if ch.abs >= 0 else "gefallen"
        if s.momentum >= 70:
            quality = "das gehört zu den kräftigeren Bewegungen der letzten Jahre"
        elif s.momentum <= 30:
            quality = "das gehört zu den schwächeren Verläufen der letzten Jahre"
        else:
            quality = "das ist ein unauffälliger Trend"
        momentum = f"In den letzten {_span(p)} ist der Wert um {_amount(ch, p.headline.format)} {direction}, {quality}."

    tone = {
        "bearish": "eher Gegenwind für Risiko",
        "neutral": "neutrales Terrain",
        "bullish": "eher Rückenwind für Risiko",
    }[p.tone]
    combined = f"Zusammen ergibt das einen Score von {s.score} von 100, also {tone}."
    return [level, momentum, combined]


def driver_sentence(p: PillarResponse) -> str:
    candidates = [c for c in p.components if c.change_13w_abs is not None]
    if not candidates:
        return ""
    def magnitude(comp) -> float:
        return abs(comp.change_13w_pct or 0.0) if comp.format in ("ratio", "price") else abs(comp.change_13w_abs or 0.0)

    c = max(candidates, key=magnitude)
    delta = c.change_13w_abs or 0.0
    rising = delta >= 0
    helps = (rising and c.sign == "+") or (not rising and c.sign == "-")
    verb = "gestiegen" if rising else "gefallen"
    if p.id == "liquidity":
        effect = "das bringt Geld ins System" if helps else "das entzieht dem Markt Geld"
    elif p.id == "structure":
        effect = "das schafft Spielraum" if helps else "das engt den Spielraum ein"
    elif p.id == "mechanics":
        effect = "das beruhigt die Technik" if helps else "das macht die Technik anfälliger"
    elif p.id == "valuation":
        effect = "das vergrößert den Sicherheitspuffer" if helps else "das vergrößert die Fallhöhe"
    else:
        effect = "das stützt die Kennzahl" if helps else "das belastet die Kennzahl"
    digits = 1 if c.format in ("index", "diffusion") else 2
    unit = "Prozentpunkte" if c.format in ("percent", "pp") else c.unit
    if c.format == "usd_millions":
        amount = de_money(delta)
    elif c.format in ("ratio", "price"):
        amount = f"{de_num(abs(c.change_13w_pct or 0.0), 1)} Prozent"
    else:
        amount = f"{de_num(abs(delta), digits)} {unit}"
    return f"Den größten Ausschlag gab zuletzt {c.label}: in {_span(p)} um {amount} {verb}, {effect}."


def regime_sentence(p: PillarResponse) -> str:
    r = p.regime
    if r is None or not r.active:
        return ""
    met = ", ".join(c.label.split(" (")[0] for c in r.criteria if c.met)
    return f"Zusatz: {r.label} ist aktiv ({r.met_count} von {r.needed} Kriterien: {met}). {r.hint}"


def build_text(p: PillarResponse) -> str:
    parts = [meaning_sentence(p), *score_sentences(p), driver_sentence(p), regime_sentence(p)]
    return " ".join(part for part in parts if part)


async def generate(p: PillarResponse) -> GenResult:
    return GenResult(text=build_text(p), model=MODEL_NAME)
