from datetime import date

from app.fred import Observation
from app.pillars.cycle import compute_composite


def obs(year: int, month: int, value: float) -> Observation:
    return Observation(date=date(year, month, 1), value=value)


def test_composite_averages_regions_and_skips_thin_months():
    phi = [obs(2026, 6, 10), obs(2026, 7, 20), obs(2026, 8, 30)]
    ny = [obs(2026, 6, -10), obs(2026, 7, 0), obs(2026, 8, 10), obs(2026, 9, 5)]
    dal = [obs(2026, 7, 10)]
    composite = compute_composite([phi, ny, dal], min_regions=2)
    assert [(o.date.month, o.value) for o in composite] == [(6, 0.0), (7, 10.0), (8, 20.0)]
    # September hat nur New York gemeldet und faellt deshalb weg


def test_composite_empty_when_nothing_overlaps():
    assert compute_composite([[obs(2026, 1, 1)], [obs(2026, 2, 1)]]) == []
