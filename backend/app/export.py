"""Statischer Export (D2): alles, was das Frontend braucht, als JSON-Dateien.

Gedacht fuer einen taeglichen Lauf in GitHub Actions: Zustand (Tagesbilder, Ereignisse) einlesen, Refresh mit
Benachrichtigung, Dateien schreiben, Zustand zuruecksichern. Das Frontend liest im Modus
NEXT_PUBLIC_DATA_MODE=static diese Dateien statt der API. Aufruf:
  python -m app.export --out ../frontend/public/data --state ../data/state.json
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import backtest, calibration, data_quality, model_card, notify, store
from .config import get_settings
from .explain import explain_pillar, resolve_provider
from .history import build_history
from .refresh import build_dashboard, refresh


def _dump_csv(path: Path, header: list[str], rows) -> None:
    """Schlichtes CSV mit Semikolon, damit Excel in deutscher Einstellung es ohne Importdialog oeffnet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")


def _stated_outlook(dashboard, report, stated_on: str) -> dict | None:
    """Was das Tool an diesem Tag behauptet hat, in der Form, in der es spaeter pruefbar ist.

    `stated_on` ist der Tag der Aussage, `data_through` das letzte Kursdatum des Backtests. Beide werden
    gebraucht: Die Trefferbilanz zaehlt ab dem Tag der Aussage, der Kursvergleich braucht den Stichtag.
    """
    zone = dashboard.consensus.zone_key
    live = next((v for v in report.variants if "live" in v.name.lower()), None)
    band = next((b for b in live.bands if b.key == zone), None) if live else None
    if not band or band.hit_rate_13w is None:
        return None
    return {
        "stated_on": stated_on, "data_through": str(report.end), "zone": zone, "rank": dashboard.consensus.score,
        "horizon_weeks": 13, "hit_rate_13w": band.hit_rate_13w, "median_13w": band.p50_fwd_13w,
        "p10_13w": band.p10_fwd_13w, "episodes": band.episodes, "benchmark": report.benchmark,
    }


async def run(out: Path, state_file: Path | None, with_backtest: bool = True, with_explanations: bool = True, log=print) -> dict:
    if state_file and state_file.exists():
        store.import_state(json.loads(state_file.read_text(encoding="utf-8")))
        log(f"Zustand eingelesen: {state_file}")
    result = await refresh(force_network=True)
    # Zwei getrennte Angaben, damit "nichts verschickt" nicht mit "kein Kanal eingerichtet" verwechselt wird.
    log(f"Refresh {result.date}: {len(result.events)} Ereignisse, gemeldet {result.notified.get('sent')}")
    log(f"Kanaele eingerichtet: {notify.configured_channels() or 'keine'}"
        + (f", Fehler: {result.notified['failed']}" if result.notified.get("failed") else ""))

    dashboard = await build_dashboard()
    _dump(out / "dashboard.json", dashboard.model_dump(mode="json"))
    history = await build_history()
    _dump(out / "history.json", history.model_dump(mode="json"))
    _dump(out / "changes.json", {"days": 365, "events": store.list_events(365, 500), "last_refresh": store.get_meta("last_refresh"),
                                 "snapshot_date": store.get_meta("last_snapshot_date"),
                                 "recording_since": store.first_snapshot_date()})
    _dump(out / "snapshots.json", {"days": 3650, "snapshots": store.list_snapshots(3650)})
    # C4: Dieselben Zahlen zum Weiterrechnen. Ohne Export bleibt jede Pruefung im Werkzeug gefangen.
    _dump_csv(out / "consensus.csv", ["Datum", "Rohwert", "Rang", "Zone", "Zyklusphase"],
              ([p.date, p.composite, p.score, p.zone_key, p.phase_key] for p in history.consensus))
    _dump_csv(out / "saeulen.csv", ["Datum", "Saeule", "Score", "Niveau", "Momentum"],
              ([pt.date, name, pt.score, pt.level, pt.momentum] for name, pts in history.pillars.items() for pt in pts))
    log(f"CSV geschrieben: {len(history.consensus)} Consensus-Zeilen")
    if with_backtest:
        report = await backtest.run_backtest(force=True)
        _dump(out / "backtest.json", asdict(report))
        # Die ausgesprochene Erwartung des Tages festhalten. Ohne dieses Protokoll laesst sich spaeter nie
        # pruefen, wie oft "8 von 10" tatsaechlich eingetroffen ist, und jede nicht gespeicherte Woche ist
        # endgueltig verloren. Der Rohwert des Index kommt dazu, damit der Abgleich ohne Fremddaten geht.
        stated = _stated_outlook(dashboard, report, result.date)
        if stated:
            store.set_meta(f"outlook:{result.date}", json.dumps(stated, ensure_ascii=False))
            log(f"Erwartung protokolliert: Zone {stated['zone']}, {stated['hit_rate_13w']} % auf 13 Wochen")
    quality = await data_quality.run_audit()
    _dump(out / "data-quality.json", data_quality.to_dict(quality))
    provider = await resolve_provider()
    explanations = {}
    # Was tatsaechlich herauskam, nicht was konfiguriert ist. Ein stiller Rueckfall auf regelbasierte Texte
    # blieb sonst wochenlang unbemerkt, waehrend die Kopfzeile weiter den konfigurierten Anbieter meldete.
    explain_stats = {"ready": 0, "fallback": 0, "reason": None, "used_model": None}
    if with_explanations:
        for p in [*dashboard.pillars, *dashboard.overlays]:
            try:
                result = await explain_pillar(p)
                explanations[p.id] = result.model_dump(mode="json")
                if result.status == "ready" and result.provider not in (None, "template"):
                    explain_stats["ready"] += 1
                    explain_stats["used_model"] = result.model
                else:
                    explain_stats["fallback"] += 1
                    explain_stats["reason"] = explain_stats["reason"] or result.reason
            except Exception as exc:  # noqa: BLE001 - eine fehlende Erklaerung darf den Export nicht stoppen
                explain_stats["fallback"] += 1
                explain_stats["reason"] = explain_stats["reason"] or f"{type(exc).__name__}"
                log(f"Erklaerung {p.id} fehlgeschlagen: {exc}")
        log(f"Erklaerungen: {explain_stats['ready']} vom Anbieter, {explain_stats['fallback']} regelbasiert"
            + (f" ({explain_stats['reason']})" if explain_stats["reason"] else ""))
    _dump(out / "explanations.json", explanations)
    settings = get_settings()
    meta = {
        "status": "ok", "generated_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"), "mode": "static",
        "fred_api_key_configured": bool(settings.fred_api_key), "anthropic_api_key_configured": bool(settings.anthropic_api_key),
        "gemini_api_key_configured": bool(settings.gemini_api_key), "explain_provider": provider,
        "explain_model": {"anthropic": settings.explain_model, "gemini": settings.gemini_model, "ollama": settings.ollama_model, "template": "regelbasiert"}.get(provider),
        "cache_ttl_seconds": settings.cache_ttl_seconds, "last_refresh": store.get_meta("last_refresh"),
        "snapshot_date": store.get_meta("last_snapshot_date"), "auto_refresh": False,
        "oldest_input": store.get_meta("oldest_input"),
        # Was das Modell ueber sich selbst sagt: Version, Parameter, Konzentration, Vergleichsfenster.
        "model": model_card.model_card(),
        "explain_stats": explain_stats,
        # Trefferbilanz: laeuft automatisch an, sobald die erste Aussage dreizehn Wochen alt ist.
        "calibration": await calibration.evaluate(),
        "recording_since": store.first_snapshot_date(),
        # Eingerichtete Kanaele, nicht die benutzten: ohne neue Ereignisse verschickt ein Lauf nichts, das sagt
        # aber nichts ueber die Konfiguration. Was wirklich rausging, steht daneben.
        "alert_channels": notify.configured_channels(),
        "alerts_sent": result.notified.get("sent", []), "alerts_failed": result.notified.get("failed", []),
        "alert_events": result.notified.get("events", 0),
    }
    _dump(out / "meta.json", meta)
    if state_file:
        _dump(state_file, store.export_state())
        log(f"Zustand gesichert: {state_file}")
    log(f"Export nach {out}: {sorted(p.name for p in out.glob('*.json'))}")
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Statischer Export des MacroPilot-Dashboards")
    parser.add_argument("--out", default="../frontend/public/data")
    parser.add_argument("--state", default="../data/state.json", help="JSON-Datei mit Tagesbildern und Ereignissen ('' = keine)")
    parser.add_argument("--no-backtest", action="store_true")
    parser.add_argument("--no-explanations", action="store_true")
    args = parser.parse_args(argv)
    base = Path(__file__).resolve().parent.parent
    out = (base / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    state = None if not args.state else ((base / args.state).resolve() if not Path(args.state).is_absolute() else Path(args.state))
    asyncio.run(run(out, state, not args.no_backtest, not args.no_explanations, log=lambda s: print(s, file=sys.stderr, flush=True)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
