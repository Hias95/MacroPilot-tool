from datetime import date, timedelta

from app.fred import Observation
from app.pillars.liquidity import compute_global_liquidity, compute_net_liquidity


def weekly(values, start=date(2026, 1, 7)):
    return [Observation(date=start + timedelta(weeks=i), value=v) for i, v in enumerate(values)]


def test_global_liquidity_converts_to_million_usd():
    walcl = weekly([1_000_000, 1_000_000])
    ecb = weekly([2_000_000, 2_000_000], start=date(2026, 1, 2))       # Mio. EUR, freitags
    boj = [Observation(date=date(2026, 1, 1), value=3_000_000)]        # 100 Mio. JPY, monatlich
    eurusd = weekly([1.10, 1.10], start=date(2026, 1, 5))
    usdjpy = weekly([150.0, 150.0], start=date(2026, 1, 5))
    out = compute_global_liquidity(walcl, ecb, boj, eurusd, usdjpy)
    assert len(out) == 2
    expected = 1_000_000 + 2_000_000 * 1.10 + 3_000_000 * 100 / 150.0
    assert round(out[-1].value) == round(expected)  # Mio. USD


def test_global_liquidity_drops_weeks_with_stale_inputs():
    walcl = weekly([1_000_000] * 12)
    ecb = weekly([2_000_000], start=date(2026, 1, 2))                  # nur eine Meldung -> nach 14 Tagen zu alt
    boj = [Observation(date=date(2026, 1, 1), value=3_000_000)]
    fx = weekly([1.0] * 12, start=date(2026, 1, 5))
    out = compute_global_liquidity(walcl, ecb, boj, fx, fx)
    assert len(out) == 2


def test_net_liquidity_treats_missing_rrp_as_zero():
    w0 = date(2025, 1, 8)
    walcl = weekly([7_000_000] * 3, start=w0)
    tga = weekly([800_000] * 3, start=w0)
    rrp = [Observation(date=w0 + timedelta(weeks=1) + timedelta(days=i), value=100.0) for i in range(8)]
    net = compute_net_liquidity(walcl, tga, rrp)
    assert [o.date for o in net] == [w0, w0 + timedelta(weeks=1), w0 + timedelta(weeks=2)]
    assert net[0].value == 7_000_000 - 800_000            # vor der ersten RRP-Meldung: 0
    assert net[1].value == 7_000_000 - 800_000 - 100.0 * 1000
