"""Tagesbilder und Ereignisse (D1/D3): was das Dashboard heute zeigt, und was sich seit dem letzten Bild geaendert hat."""

from __future__ import annotations

from datetime import date, datetime, timezone

from .consensus import MARKET_CONFIRM_LABEL, PHASE_LABEL, VETO_LABEL, ZONE_LABEL
from .schemas import DashboardResponse

PHASE_HINT = {
    "recovery": "Liquidität kommt zurück, die Konjunktur hinkt noch. Historisch beginnen hier Erholungen.",
    "expansion": "Liquidität und Konjunktur ziehen gemeinsam an.",
    "late": "Die Konjunktur läuft noch, aber die Liquidität wird knapper.",
    "downturn": "Liquidität und Konjunktur fallen. Auf die Liquiditätswende warten.",
}
CONFIRM_HINT = {
    "confirmed": "Marktsignale und Makrobild zeigen in dieselbe Richtung, historisch die verlässlichste Konstellation.",
    "market_lagging": "Das Makrobild ist besser als das, was der Markt gerade tut. Rendite historisch gleich, Rückschläge häufiger.",
    "market_ahead": "Der Markt ist optimistischer als das Makrobild, historisch die schwächste Kombination.",
}


def snapshot_from(dashboard: DashboardResponse, today: date | None = None) -> dict:
    """Kompaktes Tagesbild: nur, was sich fuer Wechsel und Rueckblick lohnt."""
    c = dashboard.consensus
    regimes = {}
    for p in [*dashboard.pillars, *dashboard.overlays]:
        if p.regime:
            regimes[p.regime.id] = {"active": p.regime.active, "label": p.regime.label, "hint": p.regime.hint, "pillar": p.name}
    return {
        "date": (today or date.today()).isoformat(),
        "taken_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "consensus": {
            "score": c.score, "composite": c.composite, "zone_key": c.zone_key, "zone": c.zone, "zone_raw_key": c.zone_raw_key,
            "weeks_in_zone": c.weeks_in_zone, "phase_key": c.phase_key, "phase": c.phase, "phase_raw_key": c.phase_raw_key,
            "weeks_in_phase": c.weeks_in_phase, "confidence": c.confidence, "market_confirmation_key": c.market_confirmation_key,
            "vetoes": list(c.vetoes),
        },
        "pillars": {p.id: {"score": p.score.score if p.score else None, "tone": p.tone, "label": p.easy_label} for p in dashboard.pillars},
        "overlays": {p.id: {"score": p.score.score if p.score else None, "tone": p.tone, "label": p.easy_label} for p in dashboard.overlays},
        "regimes": regimes,
    }


def detect_events(prev: dict | None, cur: dict) -> list[dict]:
    """Wechsel zwischen zwei Tagesbildern. Ohne Vorgaenger gibt es nichts zu melden."""
    if not prev:
        return []
    out: list[dict] = []
    day = cur["date"]
    pc, cc = prev["consensus"], cur["consensus"]

    def add(kind: str, key: str, frm, to, title: str, detail: str) -> None:
        out.append({"date": day, "kind": kind, "key": key, "from": None if frm is None else str(frm), "to": None if to is None else str(to),
                    "title": title, "detail": detail})

    if pc.get("zone_key") != cc.get("zone_key") and cc.get("zone_key"):
        add("zone", "consensus", pc.get("zone_key"), cc["zone_key"],
            f"Zone gewechselt: {ZONE_LABEL.get(pc.get('zone_key'), '?')} → {cc['zone']}",
            f"Der Consensus liegt jetzt bestätigt in der Zone {cc['zone']} (Rang {cc['score']}, besser als {cc['score']} Prozent der Wochen der letzten zehn Jahre).")
    if pc.get("phase_key") != cc.get("phase_key") and cc.get("phase_key"):
        add("phase", "consensus", pc.get("phase_key"), cc["phase_key"],
            f"Zyklusphase: {PHASE_LABEL.get(pc.get('phase_key'), '?')} → {cc['phase']}", PHASE_HINT.get(cc["phase_key"], ""))
    if pc.get("market_confirmation_key") != cc.get("market_confirmation_key") and cc.get("market_confirmation_key"):
        add("confirmation", "markets", pc.get("market_confirmation_key"), cc["market_confirmation_key"],
            f"Marktbestätigung: {MARKET_CONFIRM_LABEL.get(pc.get('market_confirmation_key'), 'unbekannt')} → {MARKET_CONFIRM_LABEL[cc['market_confirmation_key']]}",
            CONFIRM_HINT.get(cc["market_confirmation_key"], ""))
    for v in set(cc.get("vetoes", [])) - set(pc.get("vetoes", [])):
        add("veto", v, None, "on", f"Veto aktiv: {VETO_LABEL.get(v, v)}", "Ein Veto deckelt den Rohwert, weil ein Systemrisiko aktiv ist.")
    for v in set(pc.get("vetoes", [])) - set(cc.get("vetoes", [])):
        add("veto", v, "on", None, f"Veto aufgehoben: {VETO_LABEL.get(v, v)}", "Das Systemrisiko ist nach dem Modell nicht mehr aktiv.")
    for rid, cur_r in cur.get("regimes", {}).items():
        prev_r = prev.get("regimes", {}).get(rid)
        prev_active = bool(prev_r and prev_r.get("active"))
        prev_label = prev_r.get("label") if prev_r else None
        if cur_r["active"] and (not prev_active or prev_label != cur_r["label"]):
            add("regime", rid, prev_label if prev_active else None, cur_r["label"], f"{cur_r['label']} aktiv ({cur_r['pillar']})", cur_r["hint"])
        elif prev_active and not cur_r["active"]:
            add("regime", rid, prev_label, None, f"{prev_label} beendet ({cur_r['pillar']})", f"Das Regime {prev_label} ist nach dem Modell nicht mehr aktiv.")
    return out
