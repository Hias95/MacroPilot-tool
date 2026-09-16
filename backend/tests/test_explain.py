from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import config, explain
from app.explain import anthropic_provider, template
from app.main import app
from app.schemas import Change, Component, Headline, PillarResponse, ScoreBreakdown


class FakeMessages:
    def __init__(self, text: str, stop_reason: str = "end_turn"):
        self.text, self.stop_reason, self.calls = text, stop_reason, 0

    async def create(self, **kwargs):
        self.calls += 1
        self.last_kwargs = kwargs
        return SimpleNamespace(
            stop_reason=self.stop_reason, model=kwargs["model"],
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.text)],
        )


def force_provider(monkeypatch, provider: str):
    async def resolve():
        return provider

    monkeypatch.setattr(explain, "resolve_provider", resolve)


@pytest.fixture(autouse=True)
def reset_cache():
    explain.clear_cache()


def liquidity_fixture() -> PillarResponse:
    d = date(2026, 9, 9)
    return PillarResponse(
        id="liquidity", name="Liquidität", measures="x", legend="Michael Howell", status="live", tone="neutral",
        score=ScoreBreakdown(score=49, level=54, momentum=45, level_weight=0.4, momentum_window=13, lookback=520, method="t"),
        score_note="", headline=Headline(label="Net Liquidity", value=5_856_852, unit="Mio. USD", date=d),
        change_13w=Change(weeks=13, abs=-40_036, pct=-0.68),
        components=[
            Component(id="walcl", label="Fed-Bilanz", value=6_740_619, unit="Mio. USD", date=d, sign="+", change_13w_pct=0.2, change_13w_abs=15_222),
            Component(id="tga", label="Staatskonto (TGA)", value=883_335, unit="Mio. USD", date=d, sign="-", change_13w_pct=6.7, change_13w_abs=55_000),
        ],
        source="fred-csv", fetched_at=datetime.now(tz=timezone.utc), fingerprint="abc",
    )


async def test_anthropic_provider_generates_once_per_fingerprint(monkeypatch):
    fake = FakeMessages("Die Fed gibt dem Markt gerade wieder etwas mehr Luft.")
    monkeypatch.setattr(anthropic_provider, "_get_client", lambda: SimpleNamespace(messages=fake, api_key="k"))
    force_provider(monkeypatch, "anthropic")
    p = liquidity_fixture()
    first = await explain.explain_pillar(p)
    second = await explain.explain_pillar(p)
    assert first.status == "ready" and first.provider == "anthropic" and first.text.startswith("Die Fed")
    assert first.cached is False and second.cached is True and fake.calls == 1
    assert "Liquidität" in fake.last_kwargs["messages"][0]["content"]


async def test_refusal_falls_back_to_template_with_reason(monkeypatch):
    fake = FakeMessages("", stop_reason="refusal")
    monkeypatch.setattr(anthropic_provider, "_get_client", lambda: SimpleNamespace(messages=fake, api_key="k"))
    force_provider(monkeypatch, "anthropic")
    result = await explain.explain_pillar(liquidity_fixture())
    assert result.status == "ready" and result.provider == "template"
    assert "abgelehnt" in result.reason and "Score von 49" in result.text


def test_template_liquidity_text_mentions_numbers_and_driver():
    text = template.build_text(liquidity_fixture())
    assert "5,86 Billionen Dollar" in text
    assert "höher als in 54 Prozent" in text
    assert "um 40 Milliarden Dollar gefallen" in text
    assert "Score von 49 von 100" in text
    assert "Staatskonto (TGA)" in text and "entzieht dem Markt Geld" in text
    assert "kaufen" not in text.lower()


def cycle_fixture(value: float) -> PillarResponse:
    d = date(2026, 8, 1)
    return PillarResponse(
        id="cycle", name="Konjunktur", measures="x", legend="Raoul Pal", status="live", frequency="monthly", tone="neutral",
        score=ScoreBreakdown(score=47, level=40, momentum=52, level_weight=0.4, momentum_window=3, lookback=120, unit="months", method="t"),
        score_note="", headline=Headline(label="Regional-Fed-Composite", value=value, unit="Punkte", format="diffusion", date=d),
        change_13w=Change(weeks=13, abs=4.2, pct=0.0),
        components=[Component(id="phi", label="Fed Philadelphia", value=12.0, unit="Punkte", format="diffusion", date=d, change_13w_abs=9.5)],
        source="fred-csv", fetched_at=datetime.now(tz=timezone.utc), fingerprint="cyc",
    )


def test_template_cycle_uses_zero_line_and_months():
    text = template.build_text(cycle_fixture(8.9))
    assert "+8,9 Punkten, also über null" in text
    assert "In den letzten 3 Monaten ist der Wert um 4,2 Punkte gestiegen" in text
    assert "Fed Philadelphia: in 3 Monaten um 9,5 Punkte gestiegen, das stützt die Kennzahl" in text
    assert "unter null" in template.build_text(cycle_fixture(-3.0))


def test_template_structure_mentions_curve_and_inflation():
    d = date(2026, 9, 12)
    p = PillarResponse(
        id="structure", name="Inflation & Zinsen", measures="x", legend="Ray Dalio", status="live", tone="neutral",
        score=ScoreBreakdown(score=41, level=35, momentum=45, level_weight=0.4, momentum_window=13, lookback=520, method="t"),
        score_note="", headline=Headline(label="Zinskurve", value=0.42, unit="Prozentpunkte", format="pp", date=d),
        change_13w=Change(weeks=13, abs=0.15, pct=55.0),
        components=[
            Component(id="curve", label="Zinskurve 10 J minus 2 J", value=0.42, unit="%", format="pp", date=d, sign="+", change_13w_abs=0.15),
            Component(id="cpi", label="Kerninflation (Jahresrate)", value=3.1, unit="%", format="percent", date=d, sign="-", change_13w_abs=0.4),
            Component(id="real", label="Realzins 10 J (TIPS)", value=1.85, unit="%", format="percent", date=d, sign="-", change_13w_abs=-0.1),
        ],
        source="fred-csv", fetched_at=datetime.now(tz=timezone.utc), fingerprint="st",
    )
    text = template.build_text(p)
    assert "0,42 Prozentpunkte mehr Zins als zweijährige, die Zinskurve ist also normal" in text
    assert "Kerninflation liegt bei 3,1 Prozent, der Realzins bei 1,85 Prozent" in text
    assert "Kerninflation (Jahresrate): in 13 Wochen um 0,40 Prozentpunkte gestiegen, das engt den Spielraum ein" in text


def test_provider_none_disables_explanations(monkeypatch):
    monkeypatch.setattr(config.get_settings(), "explain_provider", "none")
    r = TestClient(app).get("/api/v1/pillars/cycle/explanation")
    assert r.json()["status"] == "unavailable"
