from datetime import date

from app.fred import Observation
from app.pillars.valuation import buffett_series, extreme_flag, fallhoehe_label
from app.shiller import parse_rows, shiller_date


def test_shiller_date_handles_october():
    assert shiller_date(1871.01) == date(1871, 1, 1)
    assert shiller_date(1871.1) == date(1871, 10, 1)
    assert shiller_date(2026.09) == date(2026, 9, 1)


def test_parse_rows_finds_cape_and_ecy_columns():
    header = [[""] * 18 for _ in range(8)]
    header[5][12], header[6][12], header[6][14] = "Ratio", "P/E10 or", "TR P/E10 or"
    header[5][16], header[6][16], header[7][16] = "Excess", "CAPE", "Yield"
    header[7][12], header[7][14] = "CAPE", "TR CAPE"
    rows = header + [
        [2026.08] + [""] * 11 + [41.12, "", 43.8, "", 0.0107, ""],
        [2026.09] + [""] * 11 + [40.58, "", 43.2, "", 0.0101, ""],
    ]
    cape, ecy = parse_rows(rows)
    assert [(o.date, o.value) for o in cape] == [(date(2026, 8, 1), 41.12), (date(2026, 9, 1), 40.58)]
    assert round(ecy[-1].value, 2) == 1.01


def test_buffett_ratio_in_percent():
    eq = [Observation(date=date(2026, 4, 1), value=83_050_847.0)]     # Mio. USD
    gdp = [Observation(date=date(2026, 4, 1), value=32_486.066)]       # Mrd. USD
    assert round(buffett_series(eq, gdp)[0].value) == 256


def test_labels_and_extreme_flag():
    assert fallhoehe_label(75) == "günstig" and fallhoehe_label(50) == "fair" and fallhoehe_label(30) == "teuer" and fallhoehe_label(10) == "extrem teuer"
    cape = [Observation(date=date(1996 + i // 12, 1 + i % 12, 1), value=20 + (i % 15)) for i in range(360)] + [Observation(date=date(2026, 1, 1), value=41.0)]
    buf = [Observation(date=date(1996 + i // 4, 1 + 3 * (i % 4), 1), value=100 + i) for i in range(120)] + [Observation(date=date(2026, 1, 1), value=256.0)]
    flag = extreme_flag(cape, ecy=0.9, buffett=buf)
    assert flag.active and flag.met_count == 3
    calm = extreme_flag(cape[:-1] + [Observation(date=date(2026, 1, 1), value=25.0)], ecy=3.0, buffett=buf[:-1] + [Observation(date=date(2026, 1, 1), value=150.0)])
    assert not calm.active
