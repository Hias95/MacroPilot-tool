"""D1/D3: Store, Tagesbilder, Ereignisse, Refresh-Endpunkt und Benachrichtigung (ohne Netz)."""

from datetime import date

import pytest

from app import notify, store
from app.snapshots import detect_events


def _snap(day: str, zone="neutral", phase="expansion", confirm="confirmed", vetoes=(), stress=False, label="Marktstress") -> dict:
    return {
        "date": day, "taken_at": f"{day}T07:30:00+00:00",
        "consensus": {"score": 60, "composite": 55, "zone_key": zone, "zone": {"neutral": "Neutral", "positive": "Positiv"}[zone],
                      "zone_raw_key": zone, "weeks_in_zone": 4, "phase_key": phase, "phase": {"expansion": "Aufschwung", "late": "Spätzyklus"}[phase],
                      "phase_raw_key": phase, "weeks_in_phase": 5, "confidence": "klar", "market_confirmation_key": confirm, "vetoes": list(vetoes)},
        "pillars": {}, "overlays": {},
        "regimes": {"market_stress": {"active": stress, "label": label, "hint": "Hinweis.", "pillar": "Marktsignale"}},
    }


def test_store_roundtrip_raw_snapshots_events(tmp_path, monkeypatch):
    store.save_raw("test", "k", {"a": 1}, 123.0)
    assert store.load_raw("test", "k") == ({"a": 1}, 123.0)
    assert store.load_raw("test", "missing") is None
    store.save_snapshot(_snap("2026-09-15"))
    store.save_snapshot(_snap("2026-09-16", zone="positive"))
    assert store.latest_snapshot()["date"] == "2026-09-16"
    assert store.latest_snapshot(before="2026-09-16")["date"] == "2026-09-15"
    ids = store.add_events([{"date": "2026-09-16", "kind": "zone", "key": "consensus", "from": "neutral", "to": "positive", "title": "t", "detail": "d"}])
    assert len(ids) == 1 and store.unnotified_events()[0]["title"] == "t"
    store.mark_notified(ids)
    assert store.unnotified_events() == [] and store.list_events(3650)[0]["notified"] is True
    state = store.export_state()
    assert len(state["snapshots"]) >= 2 and len(state["events"]) >= 1
    store.import_state(state)  # idempotent
    assert len(store.export_state()["events"]) == len(state["events"])


def test_detect_events_reports_each_kind_once():
    prev = _snap("2026-09-15")
    cur = _snap("2026-09-16", zone="positive", phase="late", confirm="market_ahead", vetoes=("liquidity",), stress=True)
    events = detect_events(prev, cur)
    kinds = sorted(e["kind"] for e in events)
    assert kinds == ["confirmation", "phase", "regime", "veto", "zone"]
    zone = next(e for e in events if e["kind"] == "zone")
    assert zone["from"] == "neutral" and zone["to"] == "positive" and "Positiv" in zone["title"] and "Rang 60" in zone["detail"]
    assert detect_events(None, cur) == []
    assert detect_events(cur, cur) == []
    # Stufenwechsel Marktstress -> Kapitulation zaehlt als neues Regime-Ereignis, Ende ebenfalls
    deeper = _snap("2026-09-17", zone="positive", phase="late", confirm="market_ahead", vetoes=("liquidity",), stress=True, label="Kapitulation")
    assert [e["to"] for e in detect_events(cur, deeper)] == ["Kapitulation"]
    calm = _snap("2026-09-18", zone="positive", phase="late", confirm="market_ahead", vetoes=("liquidity",), stress=False)
    assert [e["title"] for e in detect_events(deeper, calm)] == ["Kapitulation beendet (Marktsignale)"]


def test_refresh_endpoint_writes_snapshot_and_respects_token(client, monkeypatch):
    from app.config import get_settings

    r = client.post("/api/v1/refresh?force=false")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["date"] == date.today().isoformat() and body["notified"]["sent"] == []
    assert store.latest_snapshot()["consensus"]["zone_key"] in ("very_negative", "negative", "neutral", "positive", "very_positive")
    changes = client.get("/api/v1/changes?days=7").json()
    assert changes["snapshot_date"] == date.today().isoformat() and isinstance(changes["events"], list)
    assert client.get("/api/v1/snapshots?days=7").json()["snapshots"][-1]["date"] == date.today().isoformat()
    health = client.get("/health").json()
    assert health["snapshot_date"] == date.today().isoformat()
    monkeypatch.setattr(get_settings(), "refresh_token", "geheim")
    assert client.post("/api/v1/refresh").status_code == 401
    assert client.post("/api/v1/refresh?force=false", headers={"X-Refresh-Token": "geheim"}).status_code == 200


@pytest.mark.asyncio
async def test_notify_sends_pending_over_ntfy(monkeypatch):
    from app.config import get_settings

    ids = store.add_events([{"date": "2026-09-16", "kind": "zone", "key": "consensus", "from": "neutral", "to": "positive", "title": "Zone gewechselt", "detail": "Detail."}])
    sent: list[tuple[str, str]] = []

    async def fake_ntfy(title, text, tags):
        sent.append((title, text))

    monkeypatch.setattr(get_settings(), "ntfy_topic", "macropilot-test")
    monkeypatch.setattr(notify, "send_ntfy", fake_ntfy)
    result = await notify.send_pending()
    # Andere Tests koennen weitere ungemeldete Ereignisse hinterlassen haben; die Nachricht buendelt alle.
    assert result["sent"] == ["ntfy"] and sent and sent[0][0].startswith("MacroPilot") and "Zone gewechselt" in sent[0][0] + sent[0][1]
    assert all(e["id"] not in ids for e in store.unnotified_events())
    monkeypatch.setattr(get_settings(), "ntfy_topic", None)
