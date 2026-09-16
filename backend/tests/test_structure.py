from datetime import date, timedelta

from app.fred import Observation
from app.pillars.structure import aggregate, fiscal_regime, invert, uninversion_flags
from app.schemas import ScoreBreakdown
from app.services import resample_weekly, shift_dates, year_over_year
from app.treasury import parse_tbill_share


def test_resample_weekly_keeps_last_observation_per_week():
    days = [Observation(date=date(2026, 9, 7) + timedelta(days=i), value=float(i)) for i in range(10)]
    weekly = resample_weekly(days)
    assert [(o.date, o.value) for o in weekly] == [(date(2026, 9, 13), 6.0), (date(2026, 9, 16), 9.0)]


def test_year_over_year_and_shift():
    idx = [Observation(date=date(2025, m, 1), value=100.0 + m) for m in range(1, 13)]
    idx += [Observation(date=date(2026, 1, 1), value=104.03)]
    yoy = year_over_year(idx)
    assert len(yoy) == 1 and round(yoy[0].value, 2) == 3.0
    assert shift_dates(yoy, 45)[0].date == date(2026, 2, 15)


def test_invert_and_weighted_aggregate():
    b = ScoreBreakdown(score=80, level=70, momentum=90, level_weight=0.4, momentum_window=13, lookback=520, method="t")
    inv = invert(b)
    assert (inv.score, inv.level, inv.momentum) == (20, 30, 10)
    total = aggregate({"curve": b, "real": inv})  # Gewichte 0.30 und 0.25
    assert total.score == round((0.30 * 80 + 0.25 * 20) / 0.55)
    assert total.method == "weighted-component-scores"


def test_uninversion_flags_only_after_inversion_and_steep_rise():
    flat_inverted = [-0.5] * 60
    steepening = [-0.5 + 0.1 * i for i in range(1, 16)]  # steigt in 13 Wochen um 1,3 Punkte
    curve = [Observation(date=date(2024, 1, 7) + timedelta(weeks=i), value=v) for i, v in enumerate(flat_inverted + steepening)]
    flags = uninversion_flags(curve)
    assert not any(flags[:60])
    assert flags[-1] is True
    never_inverted = [Observation(date=o.date, value=o.value + 2) for o in curve]
    assert not any(uninversion_flags(never_inverted))


def test_fiscal_regime_needs_two_of_three():
    active = fiscal_regime(interest_pct=33.0, tbill_pct=22.8, repression_pp=2.3)
    assert active.active and active.met_count == 2 and [c.met for c in active.criteria] == [True, True, False]
    calm = fiscal_regime(interest_pct=12.0, tbill_pct=15.0, repression_pp=1.0)
    assert not calm.active and calm.met_count == 0


def test_parse_tbill_share():
    rows = [
        {"record_date": "2026-08-31", "security_type_desc": "Marketable", "security_class_desc": "Bills", "debt_held_public_mil_amt": "7247855.5"},
        {"record_date": "2026-08-31", "security_type_desc": "Total Marketable", "security_class_desc": "_", "debt_held_public_mil_amt": "31807141.1"},
        {"record_date": "2026-07-31", "security_type_desc": "Marketable", "security_class_desc": "Bills", "debt_held_public_mil_amt": "7000000"},
        {"record_date": "2026-07-31", "security_type_desc": "Total Nonmarketable", "security_class_desc": "_", "debt_held_public_mil_amt": "1"},
    ]
    obs = parse_tbill_share(rows)
    assert len(obs) == 1 and obs[0].date == date(2026, 8, 31) and round(obs[0].value, 2) == 22.79


def test_year_over_year_skips_missing_month_instead_of_shifting():
    from datetime import date

    from app.fred import Observation

    # 2025-10 fehlt (Regierungsstillstand): Nov 2025 muss gegen Nov 2024 rechnen, nicht gegen Dez 2024.
    months = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 13) if m != 10]
    obs = [Observation(date=date(y, m, 1), value=100.0 + (y - 2024) * 12 + m) for y, m in months]
    yoy = {o.date: o.value for o in year_over_year(obs)}
    assert date(2025, 10, 1) not in yoy
    nov = yoy[date(2025, 11, 1)]
    assert abs(nov - (123 / 111 - 1) * 100) < 1e-9
