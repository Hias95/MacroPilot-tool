from datetime import date, timedelta

import pytest

from app.fred import Observation
from app.pillars.liquidity import compute_net_liquidity
from app.scoring import percentile_rank, score_history, score_history_values, score_series
from app.services import compute_change


def test_percentile_rank_basic():
    assert percentile_rank([1, 2, 3, 4], 2.5) == 50.0
    assert percentile_rank([1, 2, 3, 4], 10) == 100.0
    assert percentile_rank([1, 2, 3, 4], 0) == 0.0
    assert percentile_rank([2, 2, 2, 2], 2) == 50.0  # Gleichstand zaehlt halb
    assert percentile_rank([], 5) == 50.0


def test_rolling_window_matches_naive_percentile():
    import random

    random.seed(1)
    vals = [random.gauss(0, 1) for _ in range(300)]
    rows = score_history_values(vals, momentum_window=5, lookback=50, min_history=10, change_mode="abs")
    for k, (_, level, _, change) in enumerate(rows):
        i = k + 10
        assert level == round(percentile_rank(vals[max(0, i - 49):i], vals[i]))
        assert change == pytest.approx(vals[i] - vals[i - 5])


def test_score_history_last_point_equals_score_series():
    vals = [100 * 1.001**i + (i % 7) for i in range(400)]
    obs = [Observation(date=date(2020, 1, 1) + timedelta(weeks=i), value=v) for i, v in enumerate(vals)]
    last = score_history(obs, min_history=104)[-1]
    single = score_series(vals)
    assert (last.score, last.level, last.momentum) == (single.score, single.level, single.momentum)
    assert last.date == obs[-1].date


def test_score_history_has_no_lookahead():
    base = [Observation(date=date(2020, 1, 1) + timedelta(weeks=i), value=100 + (i % 11)) for i in range(400)]
    shocked = base[:300] + [Observation(date=o.date, value=1e6) for o in base[300:]]
    a = score_history(base, min_history=50)
    b = score_history(shocked, min_history=50)
    assert a[:250] == b[:250]


def test_score_series_accelerating_series_has_high_momentum_and_level():
    steady = [100 * (1.001**i) for i in range(200)]
    accelerating = steady + [steady[-1] * (1.01**k) for k in range(1, 14)]
    result = score_series(accelerating, momentum_window=13, lookback=520)
    assert result is not None
    assert result.level == 100
    assert result.momentum >= 95
    assert result.score >= 95


def test_score_series_too_short_returns_none():
    assert score_series([1.0] * 10) is None


def test_compute_change_is_date_based():
    start = date(2025, 1, 1)
    daily = [Observation(date=start + timedelta(days=i), value=100 + i) for i in range(120)]
    ch = compute_change(daily, 13)
    assert ch is not None
    assert ch.abs == 91  # 13 Wochen = 91 Tage
    assert compute_change(daily, 52) is None  # nicht genug Historie


def test_net_liquidity_aligns_daily_rrp_and_converts_billions():
    w0 = date(2025, 1, 8)
    walcl = [Observation(date=w0 + timedelta(weeks=i), value=7_000_000) for i in range(3)]
    tga = [Observation(date=w0 + timedelta(weeks=i), value=800_000) for i in range(3)]
    # RRP taeglich in Mrd. USD; erster Wert erst am zweiten WALCL-Datum -> erste Woche faellt weg
    rrp = [Observation(date=w0 + timedelta(weeks=1) + timedelta(days=d), value=100.0) for d in range(0, 8)]
    net = compute_net_liquidity(walcl, tga, rrp)
    assert [o.date for o in net] == [w0, w0 + timedelta(weeks=1), w0 + timedelta(weeks=2)]
    assert net[0].value == 7_000_000 - 800_000  # vor der ersten RRP-Meldung zaehlt Reverse Repo als 0
    assert net[1].value == 7_000_000 - 800_000 - 100.0 * 1000
