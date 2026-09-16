from datetime import date, timedelta

from app.cboe import parse_history
from app.fred import Observation
from app.pillars.mechanics import panic_flag


def test_parse_cboe_history():
    text = "DATE,OPEN,HIGH,LOW,CLOSE\n09/15/2026,17.57,18.03,16.79,16.87\n01/02/1990,17.24,17.24,17.24,17.24\nbad,row\n"
    obs = parse_history(text)
    assert [(o.date, o.value) for o in obs] == [(date(1990, 1, 2), 17.24), (date(2026, 9, 15), 16.87)]


def test_panic_flag_triggers_in_top_decile():
    calm = [Observation(date=date(2016, 1, 3) + timedelta(weeks=i), value=12 + (i % 10)) for i in range(520)]
    spike = calm + [Observation(date=calm[-1].date + timedelta(weeks=1), value=45.0)]
    flag = panic_flag(spike, term_ratio=1.2)
    assert flag.active and flag.met_count == 1 and flag.criteria[1].met
    middle = calm[:-1] + [Observation(date=calm[-1].date, value=15.0)]  # mittleres Niveau, kein Extrem
    quiet = panic_flag(middle, term_ratio=0.9)
    assert not quiet.active and not quiet.criteria[1].met
