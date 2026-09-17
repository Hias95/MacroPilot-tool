from datetime import date

from tests.test_consensus import pillar

from app.easy import annotate, easy_drivers, easy_label, easy_role, easy_summary
from app.schemas import Component


def comp(cid, score, value=0.0):
    return Component(id=cid, label=cid, value=value, unit="x", format="index", date=date(2026, 9, 1), score=score)


def test_driver_labels_and_sentences():
    """Lage plus Richtung, und der Zeitraum wird ausgesprochen statt 'Trend' zu sagen."""
    p = pillar("liquidity", 72, momentum=80).model_copy(update={"tone": "bullish"})
    assert easy_label(p) == "Rückenwind"
    assert easy_summary(p) == "Es kommt netto Geld ins System. Seit drei Monaten geht es deutlich aufwärts."
    weak = pillar("cycle", 30, momentum=20).model_copy(update={"tone": "bearish"})
    assert easy_summary(weak) == "Die Industrie bremst. Seit drei Monaten geht es deutlich abwärts."
    flat = pillar("structure", 50, momentum=50).model_copy(update={"tone": "neutral"})
    assert "hat sich daran wenig geändert" in easy_summary(flat)


def test_drivers_name_the_strongest_and_weakest_part():
    p = pillar("liquidity", 55).model_copy(update={"components": [comp("net", 54), comp("global", 45), comp("tbill", 72)]})
    text = easy_drivers(p)
    assert text.startswith("Am meisten Schub gibt gerade der Anteil kurzlaufender Staatsschulden")
    assert "am wenigsten die Bilanzen der großen Notenbanken zusammen" in text


def test_drivers_say_so_when_the_parts_are_close():
    """Bei enger Streuung waere das Herausgreifen von Extremen irrefuehrend."""
    p = pillar("liquidity", 55).model_copy(update={"components": [comp("net", 52), comp("global", 48), comp("tbill", 55)]})
    assert "liegen dicht beieinander" in easy_drivers(p)


def test_drivers_fall_back_to_values_without_part_scores():
    """Die Konjunktur-Umfragen haben keine Teil-Scores, nur Werte."""
    p = pillar("cycle", 89).model_copy(update={
        "components": [comp("phi", None, 2.0), comp("ny", None, 30.0), comp("dal", None, -5.0)]})
    text = easy_drivers(p)
    assert "Am besten läuft es rund um New York" in text and "am schwächsten in Texas" in text


def test_role_names_weight_for_drivers_and_task_for_overlays():
    assert easy_role(pillar("liquidity", 55)) == "Zählt 55 von 100 Punkten im Gesamtscore. Sie wiegt damit schwerer als alle anderen."
    assert easy_role(pillar("structure", 42)) == "Zählt 30 von 100 Punkten im Gesamtscore."
    assert easy_role(pillar("valuation", 14)).startswith("Zählt nicht in den Gesamtscore")
    assert "begrenzt ihn nach oben" in easy_role(pillar("valuation", 14))
    assert "bestätigt" in easy_role(pillar("markets", 52))


def test_overlay_labels():
    val = pillar("valuation", 14, regime_active=True)
    assert easy_label(val) == "extrem teuer" and "Fallhöhe ist maximal" in easy_summary(val)
    mech = pillar("mechanics", 20, regime_active=True)
    assert easy_label(mech) == "Panik-Zone" and "Kaufzone" in easy_summary(mech)
    calm = pillar("mechanics", 75)
    assert easy_label(calm) == "ruhig"
    annotated = annotate(calm)
    assert annotated.easy_label == "ruhig" and annotated.easy_summary.startswith("Die Markttechnik ist ruhig")
    assert annotated.easy_role.startswith("Zählt nicht in den Gesamtscore")
