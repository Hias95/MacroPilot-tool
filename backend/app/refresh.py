"""Taeglicher Refresh (D1): Quellen neu laden, Verlauf neu rechnen, Tagesbild speichern, Wechsel erkennen, melden.

Laeuft im Hintergrund der API (Scheduler in main.py), per POST /api/v1/refresh oder im Export (app/export.py).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from . import backtest, cboe, fred, history, market, notify, shiller, snapshots, store, treasury
from .config import get_settings
from .consensus import build_consensus
from .easy import TREND_WEEKS, annotate
from .explain import clear_cache as clear_explanations
from .pillars import common, get_all, get_overlays
from .schemas import DashboardResponse

log = logging.getLogger("macropilot.refresh")
_running = asyncio.Lock()


@dataclass
class RefreshResult:
    date: str
    started_at: str
    finished_at: str
    events: list[dict] = field(default_factory=list)
    notified: dict = field(default_factory=dict)
    forced: bool = False


def clear_memory_caches() -> None:
    for mod in (fred, market, cboe, shiller, treasury):
        mod.clear_cache()
    common.clear_caches()
    history.clear_cache()
    backtest.clear_cache()
    clear_explanations()


async def score_changes(weeks: int = TREND_WEEKS) -> dict[str, int]:
    """Veraenderung des Scores je Saeule ueber `weeks` Wochen, aus der gemeinsamen Wochenhistorie."""
    hist = await history.build_history()
    out: dict[str, int] = {}
    for name, points in hist.pillars.items():
        if len(points) > weeks:
            out[name] = points[-1].score - points[-1 - weeks].score
    return out


async def build_dashboard() -> DashboardResponse:
    pillars, overlays = await get_all(), await get_overlays()
    state = await history.current_state()
    changes = await score_changes()
    return DashboardResponse(
        consensus=build_consensus(pillars, overlays, state),
        pillars=[annotate(p, changes.get(p.id)) for p in pillars],
        overlays=[annotate(p, changes.get(p.id)) for p in overlays],
        generated_at=datetime.now(tz=timezone.utc),
    )


async def refresh(force_network: bool = True, today: date | None = None) -> RefreshResult:
    """Ein kompletter Durchlauf. force_network leert die Speicher-Caches, damit die Quellen neu befragt werden
    (bei Netzausfall greift die Platte)."""
    async with _running:
        started = datetime.now(tz=timezone.utc)
        if force_network:
            clear_memory_caches()
        dashboard = await build_dashboard()
        snap = snapshots.snapshot_from(dashboard, today)
        prev = store.latest_snapshot(before=snap["date"])
        events = snapshots.detect_events(prev, snap)
        store.save_snapshot(snap)
        if events:
            ids = store.add_events(events)
            for e, i in zip(events, ids):
                e["id"] = i
        notified = await notify.send_pending()
        finished = datetime.now(tz=timezone.utc)
        store.set_meta("last_refresh", finished.isoformat(timespec="seconds"))
        store.set_meta("last_snapshot_date", snap["date"])
        # Aeltester Eingang ueber alle Saeulen: Der Gesamtscore mischt Daten von einem bis siebzehn Tagen Alter.
        # Ohne diese Angabe wirkt die Kopfzeile ("Stand heute") frischer als die Grundlage tatsaechlich ist.
        dates = [p.headline.date for p in (*dashboard.pillars, *dashboard.overlays) if p.headline]
        if dates:
            store.set_meta("oldest_input", min(dates).isoformat())
        log.info("Refresh %s: %d Ereignisse, gemeldet %s", snap["date"], len(events), notified.get("sent"))
        return RefreshResult(date=snap["date"], started_at=started.isoformat(timespec="seconds"),
                             finished_at=finished.isoformat(timespec="seconds"), events=events, notified=notified, forced=force_network)


def last_refresh() -> datetime | None:
    raw = store.get_meta("last_refresh")
    return datetime.fromisoformat(raw) if raw else None


def _next_run(now: datetime) -> datetime:
    s = get_settings()
    target = now.replace(hour=s.refresh_hour, minute=s.refresh_minute, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


async def scheduler() -> None:
    """Beim Start ein Refresh, falls heute noch keiner lief, danach taeglich zur eingestellten Uhrzeit."""
    s = get_settings()
    await asyncio.sleep(3)
    try:
        last = last_refresh()
        if last is None or last.astimezone().date() < datetime.now().date():
            await refresh(force_network=False)
    except Exception as exc:  # noqa: BLE001 - der Scheduler darf nie sterben
        log.warning("Start-Refresh fehlgeschlagen: %s", exc)
    while True:
        now = datetime.now().astimezone()
        wait = (_next_run(now) - now).total_seconds()
        log.info("Naechster Refresh in %.0f Minuten (%02d:%02d)", wait / 60, s.refresh_hour, s.refresh_minute)
        await asyncio.sleep(wait)
        try:
            await refresh(force_network=True)
        except Exception as exc:  # noqa: BLE001
            log.warning("Refresh fehlgeschlagen: %s", exc)
