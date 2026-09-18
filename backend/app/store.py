"""Persistenz (D1): SQLite unter backend/data. Drei Dinge landen dort.

  raw_cache  Rohdaten der Quellen (FRED, Yahoo, CBOE, Shiller, Treasury) als Pickle, damit ein Neustart
             nicht jede Quelle befragt und ein Netzausfall nicht das Dashboard leert.
  snapshots  Ein Tagesbild des Dashboards (Rang, Zone, Phase, Scores, Flags): die erste Point-in-time-Aufzeichnung
             dessen, was das Tool tatsaechlich gezeigt hat.
  events     Erkannte Wechsel (Zone, Phase, Regime-Flags, Marktbestaetigung, Vetos) fuer Hinweise und die
             Aenderungsliste im Dashboard.
Nur Standardbibliothek. Zugriffe sind kurz und laufen synchron unter einem Lock.
"""

from __future__ import annotations

import json
import pickle
import sqlite3
import threading
import time
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .config import get_settings

_lock = threading.Lock()
_initialised: set[str] = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_cache (kind TEXT NOT NULL, key TEXT NOT NULL, payload BLOB NOT NULL, fetched_at REAL NOT NULL,
                                      PRIMARY KEY (kind, key));
CREATE TABLE IF NOT EXISTS snapshots (date TEXT PRIMARY KEY, taken_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, date TEXT NOT NULL, kind TEXT NOT NULL,
                                   key TEXT NOT NULL, from_value TEXT, to_value TEXT, title TEXT NOT NULL, detail TEXT NOT NULL,
                                   notified INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def db_path() -> Path:
    return get_settings().data_path / "macropilot.sqlite"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    key = str(path)
    if key not in _initialised:
        conn.executescript(SCHEMA)
        _initialised.add(key)
    return conn


# --- Rohdaten-Cache -------------------------------------------------------------------------------------

def load_raw(kind: str, key: str) -> tuple[Any, float] | None:
    """(Objekt, fetched_at) oder None. Unlesbare Eintraege (andere Codeversion) werden ignoriert."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT payload, fetched_at FROM raw_cache WHERE kind = ? AND key = ?", (kind, key)).fetchone()
    if not row:
        return None
    try:
        return pickle.loads(row[0]), float(row[1])
    except Exception:  # noqa: BLE001 - alte Pickles duerfen nie den Start verhindern
        return None


def save_raw(kind: str, key: str, obj: Any, fetched_at: float | None = None) -> None:
    payload = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
    with _lock, _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO raw_cache (kind, key, payload, fetched_at) VALUES (?, ?, ?, ?)",
                     (kind, key, payload, fetched_at if fetched_at is not None else time.time()))


def raw_cache_stats() -> dict:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT kind, COUNT(*), MIN(fetched_at), MAX(fetched_at) FROM raw_cache GROUP BY kind").fetchall()
    return {k: {"entries": n, "oldest": lo, "newest": hi} for k, n, lo, hi in rows}


# --- Tagesbilder ----------------------------------------------------------------------------------------

def save_snapshot(snapshot: dict) -> None:
    with _lock, _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO snapshots (date, taken_at, payload) VALUES (?, ?, ?)",
                     (snapshot["date"], snapshot["taken_at"], json.dumps(snapshot, ensure_ascii=False)))


def latest_snapshot(before: str | None = None) -> dict | None:
    """Juengstes Tagesbild, optional strikt vor einem Datum (ISO)."""
    with _lock, _connect() as conn:
        if before:
            row = conn.execute("SELECT payload FROM snapshots WHERE date < ? ORDER BY date DESC LIMIT 1", (before,)).fetchone()
        else:
            row = conn.execute("SELECT payload FROM snapshots ORDER BY date DESC LIMIT 1").fetchone()
    return json.loads(row[0]) if row else None


def list_snapshots(days: int = 90) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT payload FROM snapshots WHERE date >= ? ORDER BY date", (cutoff,)).fetchall()
    return [json.loads(r[0]) for r in rows]


# --- Ereignisse -----------------------------------------------------------------------------------------

def add_events(events: Iterable[dict]) -> list[int]:
    ids: list[int] = []
    with _lock, _connect() as conn:
        for e in events:
            cur = conn.execute(
                "INSERT INTO events (at, date, kind, key, from_value, to_value, title, detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (e.get("at") or datetime.now(tz=timezone.utc).isoformat(), e["date"], e["kind"], e["key"],
                 e.get("from"), e.get("to"), e["title"], e["detail"]),
            )
            ids.append(int(cur.lastrowid))
    return ids


def _row_to_event(r: tuple) -> dict:
    return {"id": r[0], "at": r[1], "date": r[2], "kind": r[3], "key": r[4], "from": r[5], "to": r[6],
            "title": r[7], "detail": r[8], "notified": bool(r[9])}


def list_events(days: int = 90, limit: int = 200) -> list[dict]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM events WHERE date >= ? ORDER BY date DESC, id DESC LIMIT ?", (cutoff, limit)).fetchall()
    return [_row_to_event(r) for r in rows]


def unnotified_events() -> list[dict]:
    with _lock, _connect() as conn:
        rows = conn.execute("SELECT * FROM events WHERE notified = 0 ORDER BY date, id").fetchall()
    return [_row_to_event(r) for r in rows]


def mark_notified(ids: Iterable[int]) -> None:
    ids = list(ids)
    if not ids:
        return
    with _lock, _connect() as conn:
        conn.executemany("UPDATE events SET notified = 1 WHERE id = ?", [(i,) for i in ids])


# --- Meta und Export ------------------------------------------------------------------------------------

def get_meta(key: str) -> str | None:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_meta(key: str, value: str) -> None:
    with _lock, _connect() as conn:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))


def first_snapshot_date() -> str | None:
    """Tag des aeltesten Tagesbilds. Die Aenderungsliste darf nicht "letzte 365 Tage" behaupten, wenn erst
    seit drei Tagen aufgezeichnet wird."""
    with _lock, _connect() as conn:
        row = conn.execute("SELECT MIN(date) FROM snapshots").fetchone()
    return row[0] if row and row[0] else None


def export_state() -> dict:
    """Tagesbilder, Ereignisse und Meta als JSON-faehiges Dict (fuer den Export in ein Repository)."""
    with _lock, _connect() as conn:
        snaps = [json.loads(r[0]) for r in conn.execute("SELECT payload FROM snapshots ORDER BY date").fetchall()]
        events = [_row_to_event(r) for r in conn.execute("SELECT * FROM events ORDER BY id").fetchall()]
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    return {"snapshots": snaps, "events": events, "meta": meta}


def import_state(state: dict) -> None:
    """Spielt einen Export ein; Eintraege gleichen Datums oder gleicher Kennung werden ersetzt."""
    with _lock, _connect() as conn:
        for s in state.get("snapshots", []):
            conn.execute("INSERT OR REPLACE INTO snapshots (date, taken_at, payload) VALUES (?, ?, ?)",
                         (s["date"], s["taken_at"], json.dumps(s, ensure_ascii=False)))
        for e in state.get("events", []):
            conn.execute(
                "INSERT OR REPLACE INTO events (id, at, date, kind, key, from_value, to_value, title, detail, notified) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (e.get("id"), e["at"], e["date"], e["kind"], e["key"], e.get("from"), e.get("to"), e["title"], e["detail"],
                 1 if e.get("notified") else 0),
            )
        for k, v in state.get("meta", {}).items():
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (k, v))
