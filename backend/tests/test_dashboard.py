import pytest
from fastapi.testclient import TestClient

from app import fred
from app.main import app


def test_dashboard_returns_four_pillars_and_consensus(client):
    r = client.get("/api/v1/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [p["id"] for p in body["pillars"]] == ["liquidity", "cycle", "structure"]
    assert [p["id"] for p in body["overlays"]] == ["valuation", "mechanics", "markets"]
    liq = body["pillars"][0]
    assert liq["status"] == "live"
    assert liq["headline"]["label"] == "Net Liquidity"
    assert 0 <= liq["score"]["score"] <= 100
    assert liq["score"]["method"] == "weighted-signal-scores"
    assert [c["id"] for c in liq["components"]] == ["net", "global", "tbill", "walcl", "tga", "rrp"]
    assert all(liq["components"][i]["score"] is not None for i in range(3))
    assert liq["components"][2]["format"] == "percent"
    assert len(liq["history"]) >= 52  # lange Rohwert-Historie, Zeithorizont filtert das Frontend
    cyc = body["pillars"][1]
    assert cyc["status"] == "live" and cyc["frequency"] == "monthly"
    assert cyc["headline"]["format"] == "diffusion" and "Regional" in cyc["headline"]["label"]
    assert cyc["score"]["unit"] == "months" and cyc["score"]["momentum_window"] == 3
    assert len(cyc["components"]) == 3 and len(cyc["history"]) >= 60
    mk = body["overlays"][2]
    assert mk["status"] == "live" and mk["headline"]["format"] == "ratio" and mk["kind"] == "overlay"
    assert mk["regime"]["id"] == "market_stress" and mk["regime"]["label"] in ("Marktstress", "Kapitulation")
    assert [c["id"] for c in mk["components"]] == ["breadth", "risk", "real", "credit"]
    assert mk["name"] == "Marktsignale" and mk["components"][1]["format"] == "price"
    assert all(0 <= c["score"] <= 100 for c in mk["components"])
    assert mk["score"]["method"] == "mean-of-signal-scores"
    st = body["pillars"][2]
    assert st["status"] == "live" and st["headline"]["format"] == "pp"
    assert [c["id"] for c in st["components"]] == ["curve", "real", "cpi", "dsr", "interest"]
    assert [c["sign"] for c in st["components"]] == ["+", "-", "-", "-", "-"]
    assert st["score"]["method"] == "weighted-component-scores"
    assert st["regime"]["id"] == "fiscal_dominance" and len(st["regime"]["criteria"]) == 3
    assert all(0 <= c["score"] <= 100 for c in st["components"])
    assert all(p["status"] == "live" and p["kind"] == "driver" for p in body["pillars"])
    ov = body["overlays"]
    assert [o["id"] for o in ov] == ["valuation", "mechanics", "markets"] and all(o["kind"] == "overlay" for o in ov)
    assert [c["id"] for c in ov[0]["components"]] == ["cape", "ecy", "buffett"] and ov[0]["regime"]["id"] == "extreme_valuation"
    assert [c["id"] for c in ov[1]["components"]] == ["vix", "term", "skew"]
    assert ov[1]["regime"]["id"] == "panic_zone" and 0 <= ov[1]["score"]["score"] <= 100
    assert "Fallhöhe" in ov[0]["score_note"]
    assert all(p["easy_label"] and p["easy_summary"] for p in body["pillars"] + ov)
    assert isinstance(body["consensus"]["score"], int)
    assert body["consensus"]["method"] == "macropilot-v2-rank" and body["consensus"]["why"]
    assert body["consensus"]["zone_key"] in ("very_negative", "negative", "neutral", "positive", "very_positive")
    assert body["consensus"]["composite"] is not None and body["consensus"]["weeks_in_zone"] is not None
    assert body["consensus"]["phase_key"] in ("recovery", "expansion", "late", "downturn")
    assert body["consensus"]["weeks_in_phase"] is not None and body["consensus"]["valuation_cap"] is not None
    assert body["consensus"]["zone"] in {"Stark negativ", "Negativ", "Neutral", "Positiv", "Stark positiv"}
    assert set(body["consensus"]["pillar_scores"]) == {"liquidity", "cycle", "structure"}
    assert "markets" in body["consensus"]["overlay_scores"] and body["consensus"]["market_confirmation_key"] in ("confirmed", "market_ahead", "market_lagging")


def test_single_pillar_and_unknown_id(client):
    assert client.get("/api/v1/pillars/structure").json()["status"] == "live"
    assert client.get("/api/v1/pillars/nope").status_code == 422


def test_fred_error_maps_to_502(monkeypatch):
    async def boom(*args, **kwargs):
        raise fred.FredError("FRED kaputt")

    monkeypatch.setattr(fred, "fetch_series", boom)
    r = TestClient(app).get("/api/v1/dashboard")
    assert r.status_code == 502 and "FRED kaputt" in r.json()["detail"]
