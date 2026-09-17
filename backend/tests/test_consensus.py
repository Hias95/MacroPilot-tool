from datetime import date, datetime, timezone

from app.consensus import ConsensusState, Overlay, Snapshot, build_consensus, core, zone_for
from app.schemas import Change, Headline, PillarResponse, RegimeCriterion, RegimeFlag, ScoreBreakdown


def snap(score, momentum=60, change=1.0):
    return Snapshot(score=score, momentum=momentum, change=change)


def drivers(liq=60, cyc=60, mk=60, st=60, liq_change=1.0, cyc_change=1.0):
    return {"liquidity": snap(liq, change=liq_change), "cycle": snap(cyc, change=cyc_change), "markets": snap(mk), "structure": snap(st)}


def test_core_is_weighted_mean_without_overlays():
    from app.model_config import CONSENSUS_WEIGHTS as W

    r = core(drivers(liq=80, cyc=60, mk=40, st=20))
    assert round(r.core, 2) == round(W["liquidity"] * 80 + W["cycle"] * 60 + W["structure"] * 20, 2)
    assert r.score == round(r.core) and r.cap is None and r.vetoes == []


def test_zone_bands_and_phase_matrix():
    assert zone_for(5)[1] == "Stark negativ" and zone_for(20)[1] == "Negativ" and zone_for(50)[1] == "Neutral"
    assert zone_for(80)[1] == "Positiv" and zone_for(95)[1] == "Stark positiv"
    assert core(drivers(liq_change=1, cyc_change=-1)).phase_raw_key == "recovery"
    assert core(drivers(liq_change=1, cyc_change=1)).phase_raw_key == "expansion"
    assert core(drivers(liq_change=-1, cyc_change=1)).phase_raw_key == "late"
    assert core(drivers(liq_change=-1, cyc_change=-1)).phase_raw_key == "downturn"


def test_mechanics_is_contrarian_since_c2():
    calm = core(drivers(), mechanics=Overlay(score=100))
    stressed = core(drivers(), mechanics=Overlay(score=0))
    panic = core(drivers(), mechanics=Overlay(score=0, regime_active=True))
    assert calm.mechanics_adjustment == -5.0 and stressed.mechanics_adjustment == 5.0 and panic.mechanics_adjustment == 5.0


def test_valuation_caps_upside():
    r = core(drivers(liq=90, cyc=90, mk=90, st=90), valuation=Overlay(score=0))
    assert r.valuation_cap == 60.0 and r.cap == 60.0 and r.score == 60
    cheap = core(drivers(liq=90, cyc=90, mk=90, st=90), valuation=Overlay(score=100))
    assert cheap.score == 90


def test_vetoes_cap_score():
    assert core(drivers(liq=10)).vetoes == ["liquidity"] and core(drivers(liq=10, cyc=90, mk=90, st=90)).score <= 35
    assert core(drivers(st=10)).vetoes == ["structure"] and core(drivers(st=10, liq=90, cyc=90, mk=90)).score <= 30
    combo = core(drivers(liq=90, cyc=90, mk=90, st=90), valuation=Overlay(score=10, regime_active=True), mechanics=Overlay(score=20))
    assert "valuation_mechanics" in combo.vetoes and combo.score <= 40
    in_panic = core(drivers(liq=90, cyc=90, mk=90, st=90), valuation=Overlay(score=10, regime_active=True), mechanics=Overlay(score=20, regime_active=True))
    assert "valuation_mechanics" not in in_panic.vetoes


def pillar(pid, score, momentum=60, change=1.0, regime_active=False):
    labels = {"valuation": "Extreme Bewertung", "mechanics": "Panik-Zone", "markets": "Marktstress"}
    regime = RegimeFlag(id="x", label=labels[pid], active=regime_active, met_count=2, needed=2, hint="Rückschläge verstärken sich.",
                        criteria=[RegimeCriterion(label="a", value_text="b", met=True)]) if pid in labels else None
    return PillarResponse(
        id=pid, name=pid, measures="x", legend="y", status="live", tone="neutral", kind="overlay" if regime else "driver",
        score=ScoreBreakdown(score=score, level=score, momentum=momentum, level_weight=0.4, momentum_window=13, lookback=520, method="t"),
        score_note="", headline=Headline(label="h", value=1.0, unit="u", format="index", date=date(2026, 9, 1)),
        change_13w=Change(weeks=13, abs=change, pct=change), regime=regime,
        source="t", fetched_at=datetime.now(tz=timezone.utc), fingerprint="f",
    )


def test_build_consensus_ranks_against_window_and_uses_confirmed_zone():
    drivers_ = [pillar("liquidity", 54, 53, -1.0), pillar("cycle", 93, 95, 20.0), pillar("markets", 52), pillar("structure", 44)]
    overlays = [pillar("valuation", 14, regime_active=True), pillar("mechanics", 49)]
    # Kern (Gewichte 55/15/30) = 0.55*54 + 0.15*93 + 0.30*44 = 56.85, Mechanik 49 -> +0.1 (Kontra), Deckel greift nicht -> 57.
    window = [35.0 + i * 0.1 for i in range(300)]  # Rohwerte 35 bis 65: ein Rohwert von 57 liegt bei etwa 73 %
    state = ConsensusState(window=window, zone_key="neutral", weeks_in_zone=9, phase_key="late", weeks_in_phase=6)
    c = build_consensus(drivers_, overlays, state)
    assert c.method == "macropilot-v2-rank" and c.composite == 57 and 70 <= c.score <= 76
    assert c.zone == "Neutral" and c.zone_raw_key == "positive" and c.weeks_in_zone == 9
    assert c.phase == "Spätzyklus" and c.weeks_in_phase == 6 and c.valuation_cap == 65.6
    assert "besser als in" in c.why and "Rohwert 57" in c.why and "noch unbestätigt" in c.why
    assert "Am stärksten stützt Konjunktur (93)" in c.why and "Deckel bei 66" in c.why
    plain = build_consensus(drivers_, overlays)
    assert plain.score == 57 and plain.zone_raw_key == plain.zone_key


def test_build_consensus_falls_back_without_scores():
    drivers_ = [pillar("liquidity", 40), pillar("cycle", 60), pillar("structure", 50)]
    drivers_[2].score = None
    assert build_consensus(drivers_).method == "mean-fallback"


def test_core_accepts_calibration_params():
    from app.consensus import ConsensusParams

    drivers_ = {
        "liquidity": Snapshot(80, 60, 1.0), "cycle": Snapshot(40, 40, -1.0),
        "markets": Snapshot(20, 50, 0.0), "structure": Snapshot(60, 50, 0.0),
    }
    default = core(drivers_, Overlay(10), Overlay(20))
    assert default.valuation_cap == 64 and default.mechanics_adjustment == 3  # Kontra: Stress hebt an
    structure_only = ConsensusParams(weights={"liquidity": 0, "markets": 0, "cycle": 0, "structure": 1},
                                     mechanics_range=0, valuation_cap={"base": 100, "slope": 0}, markets_sign=-1)
    r = core(drivers_, Overlay(10), Overlay(20), structure_only)
    assert r.core == 60 and r.mechanics_adjustment == 0 and r.valuation_cap == 100 and r.score == 60
    inverted = ConsensusParams(weights={"liquidity": 0, "markets": 1, "cycle": 0, "structure": 0}, markets_sign=-1,
                               valuation_cap={"base": 100, "slope": 0}, mechanics_range=0)
    assert core(drivers_, None, None, inverted).core == 80


def test_market_confirmation_and_stress_flag():
    from app.consensus import market_confirmation
    from app.pillars.markets import stress_flag

    assert market_confirmation(70, 60) == "confirmed" and market_confirmation(30, 20) == "confirmed"
    assert market_confirmation(30, 60) == "market_ahead" and market_confirmation(70, 40) == "market_lagging"
    assert market_confirmation(None, 50) is None
    assert stress_flag(45).active is False and stress_flag(45).label == "Marktstress"
    assert stress_flag(25).active and stress_flag(25).label == "Marktstress" and stress_flag(25).met_count == 1
    assert stress_flag(15).active and stress_flag(15).label == "Kapitulation" and stress_flag(15).met_count == 2
    drivers_ = [pillar("liquidity", 54, 53, -1.0), pillar("cycle", 93, 95, 20.0), pillar("structure", 44)]
    overlays = [pillar("valuation", 14, regime_active=True), pillar("mechanics", 49), pillar("markets", 25, regime_active=True)]
    c = build_consensus(drivers_, overlays)
    assert c.market_confirmation_key == "market_lagging" and c.market_confirmation == "Markt zögert"
    assert "Marktsignale 25" in c.why and "Rückschläge" in c.why or "Marktstress" in c.why


def test_pending_zone_reports_streak_and_confirmation_date():
    """Der Widerspruch zwischen Nadel und Zonenwort wird zur Vorschau: wie lange schon, und ab wann es gilt."""
    drivers_ = [pillar("liquidity", 54, 53, -1.0), pillar("cycle", 93, 95, 20.0), pillar("structure", 44)]
    overlays = [pillar("valuation", 14, regime_active=True), pillar("mechanics", 49)]
    window = [35.0 + i * 0.1 for i in range(300)]
    base = dict(window=window, zone_key="neutral", weeks_in_zone=9, phase_key="late", weeks_in_phase=6,
                last_date=date(2026, 9, 13))

    # Zweite Woche in Folge: noch eine fehlt, Bestaetigung eine Woche nach dem letzten Rastertag.
    c = build_consensus(drivers_, overlays, ConsensusState(zone_pending_key="positive", zone_pending_weeks=2, **base))
    assert c.zone_key == "neutral" and c.zone_pending_key == "positive"
    assert c.zone_pending_weeks == 2 and c.zone_confirm_weeks == 3
    assert c.zone_change_date == date(2026, 9, 20)
    assert "die 2. Woche in Folge" in c.why and "20.09.2026" in c.why

    # Die Historie kennt einen anderen Kandidaten: der Lauf beginnt mit dieser Woche neu.
    # Der letzte Rastertag ist dann selbst die erste Woche, es fehlen noch zwei.
    fresh = build_consensus(drivers_, overlays, ConsensusState(zone_pending_key="negative", zone_pending_weeks=2, **base))
    assert fresh.zone_pending_weeks == 1 and fresh.zone_change_date == date(2026, 9, 27)

    # Stimmt die Zone mit der bestaetigten ueberein, schwebt nichts.
    quiet = build_consensus(drivers_, overlays, ConsensusState(zone_pending_key=None, zone_pending_weeks=0,
                                                              **{**base, "zone_key": "positive"}))
    assert quiet.zone_pending_key is None and quiet.zone_change_date is None and quiet.zone_pending_weeks == 0
