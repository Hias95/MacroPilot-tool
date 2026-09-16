from tests.test_consensus import pillar

from app.easy import annotate, easy_label, easy_summary


def test_driver_labels_and_sentences():
    p = pillar("liquidity", 72, momentum=80)
    p = p.model_copy(update={"tone": "bullish"})
    assert easy_label(p) == "Rückenwind"
    assert easy_summary(p) == "Es kommt netto Geld ins System. Der Trend zeigt klar nach oben."
    weak = pillar("cycle", 30, momentum=20).model_copy(update={"tone": "bearish"})
    assert easy_summary(weak) == "Die Industrie bremst. Der Trend zeigt nach unten."


def test_overlay_labels():
    val = pillar("valuation", 14, regime_active=True)
    assert easy_label(val) == "extrem teuer" and "Fallhöhe ist maximal" in easy_summary(val)
    mech = pillar("mechanics", 20, regime_active=True)
    assert easy_label(mech) == "Panik-Zone" and "Kaufzone" in easy_summary(mech)
    calm = pillar("mechanics", 75)
    assert easy_label(calm) == "ruhig"
    annotated = annotate(calm)
    assert annotated.easy_label == "ruhig" and annotated.easy_summary.startswith("Die Markttechnik ist ruhig")
