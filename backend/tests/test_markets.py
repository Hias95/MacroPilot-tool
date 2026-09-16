from datetime import date, timedelta

from app.fred import Observation
from app.pillars.markets import aggregate, compute_ratio
from app.schemas import ScoreBreakdown


def series(values, start=date(2026, 1, 5), step_days=7):
    return [Observation(date=start + timedelta(days=i * step_days), value=v) for i, v in enumerate(values)]


def test_ratio_uses_only_common_dates_and_skips_zero_denominator():
    num = series([10, 20, 30, 40])
    den = series([2, 0, 3], start=date(2026, 1, 12))  # beginnt eine Woche spaeter, enthaelt eine 0
    ratio = compute_ratio(num, den)
    assert [(o.date, o.value) for o in ratio] == [(date(2026, 1, 12), 10.0), (date(2026, 1, 26), 40 / 3)]


def test_aggregate_averages_scores():
    def bd(score, level, momentum):
        return ScoreBreakdown(score=score, level=level, momentum=momentum, level_weight=0.4, momentum_window=13, lookback=520, method="t")

    total = aggregate([bd(80, 70, 90), bd(40, 30, 50)])
    assert (total.score, total.level, total.momentum) == (60, 50, 70)
    assert total.method == "mean-of-signal-scores"


def test_single_series_signal_and_scale():
    num = series([2, 4])
    assert [o.value for o in compute_ratio(num, None)] == [2.0, 4.0]
    assert [o.value for o in compute_ratio(num, series([1000, 1000]), scale=1000.0)] == [2.0, 4.0]
