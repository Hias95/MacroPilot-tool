from datetime import date


def test_history_endpoint_returns_weekly_grid(client):
    r = client.get("/api/v1/history?years=5")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["frequency"] == "weekly"
    assert set(body["pillars"]) == {"liquidity", "cycle", "markets", "structure", "mechanics", "valuation"}
    for pts in body["pillars"].values():
        assert len(pts) > 100
        dates = [date.fromisoformat(p["date"]) for p in pts]
        assert all((b - a).days == 7 for a, b in zip(dates, dates[1:]))
        assert all(0 <= p["score"] <= 100 and 0 <= p["level"] <= 100 for p in pts)
    assert len(body["consensus"]) > 100
    assert all(p["zone_key"] in ("very_negative", "negative", "neutral", "positive", "very_positive") for p in body["consensus"])
    assert all(p["phase_key"] in ("recovery", "expansion", "late", "downturn") for p in body["consensus"])
    assert all(0 <= p["composite"] <= 100 and 0 <= p["score"] <= 100 for p in body["consensus"])
    # Synthetische Daten enden vor dem Rasterende; der letzte Consensus-Punkt darf hoechstens 60 Tage zurueckliegen.
    assert (date.fromisoformat(body["end"]) - date.fromisoformat(body["consensus"][-1]["date"])).days <= 60


def test_history_years_filter_and_cache(client):
    full = client.get("/api/v1/history").json()
    short = client.get("/api/v1/history?years=2").json()
    assert len(short["consensus"]) < len(full["consensus"])
    assert short["consensus"][-1] == full["consensus"][-1]


def test_rolling_rank_uses_only_previous_values():
    from app.history import rolling_rank

    ranks = rolling_rank([1.0, 2.0, 3.0, 4.0, 2.5], window=3, min_history=2)
    assert ranks[:2] == [None, None]
    assert ranks[2] == 100.0 and ranks[3] == 100.0
    assert ranks[4] == 100.0 * (1 + 0.5 * 0) / 3 or abs(ranks[4] - 33.3) < 0.5
