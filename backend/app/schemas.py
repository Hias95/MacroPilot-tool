"""Antwort-Modelle der API (spiegeln sich 1:1 in frontend/src/lib/api.ts)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

PillarId = Literal["liquidity", "cycle", "markets", "structure", "mechanics", "valuation"]
PillarKind = Literal["driver", "overlay"]
PillarStatus = Literal["live", "demo"]
Tone = Literal["bearish", "neutral", "bullish"]
ValueFormat = Literal["usd_millions", "index", "diffusion", "ratio", "percent", "pp", "price"]
Frequency = Literal["weekly", "monthly"]
WindowUnit = Literal["weeks", "months", "quarters"]


class Point(BaseModel):
    date: date
    value: float


class Change(BaseModel):
    weeks: int = Field(description="Vergleichszeitraum in Wochen")
    abs: float = Field(description="Absolute Veraenderung in Einheiten der Serie")
    pct: float = Field(description="Prozentuale Veraenderung")


class SeriesResponse(BaseModel):
    series_id: str
    title: str
    unit: str
    frequency: str
    latest: Point
    previous: Point | None
    change_1w: Change | None
    change_13w: Change | None
    change_52w: Change | None
    history: list[Point]
    source: str
    cached: bool
    fetched_at: datetime


class ScoreBreakdown(BaseModel):
    score: int = Field(ge=0, le=100)
    level: int = Field(ge=0, le=100, description="Perzentil des aktuellen Niveaus ueber lookback_weeks")
    momentum: int = Field(ge=0, le=100, description="Perzentil der aktuellen Veraenderung ueber momentum_window_weeks")
    level_weight: float
    momentum_window: int = Field(description="Fenster fuer das Momentum, in `unit`")
    lookback: int = Field(description="Historie fuer das Niveau-Perzentil, in `unit`")
    unit: WindowUnit = "weeks"
    method: str
    change: float | None = Field(default=None, description="Veraenderung der Basis-Serie ueber momentum_window (Prozent oder absolut)")


class Headline(BaseModel):
    label: str
    value: float
    unit: str
    format: ValueFormat = "usd_millions"
    date: date
    sign: Literal["+", "-"] = Field("+", description="Ist ein steigender Wert gut (+) oder schlecht (-) fuer den Score")


class Component(BaseModel):
    id: str
    label: str
    value: float
    unit: str
    format: ValueFormat = "usd_millions"
    date: date
    sign: Literal["+", "-"] = Field("+", description="Geht der Wert positiv oder negativ in die Hauptkennzahl ein")
    change_13w_pct: float | None = None
    change_13w_abs: float | None = None
    score: int | None = Field(None, ge=0, le=100, description="Teil-Score, falls der Bestandteil eigen bewertet wird")
    note: str | None = None


class RegimeCriterion(BaseModel):
    label: str
    value_text: str
    met: bool


class RegimeFlag(BaseModel):
    id: str
    label: str
    active: bool
    met_count: int
    needed: int
    criteria: list[RegimeCriterion]
    hint: str = Field(description="Was das Regime fuer Anleger bedeutet, ein Satz")


class PillarResponse(BaseModel):
    id: PillarId
    name: str = Field(description="Was die Saeule misst, z. B. Liquiditaet")
    measures: str = Field(description="Ein Satz: was genau gemessen wird")
    legend: str = Field(description="Denkschule, z. B. Michael Howell")
    status: PillarStatus
    kind: PillarKind = "driver"
    frequency: Frequency = "weekly"
    tone: Tone
    score: ScoreBreakdown | None
    score_note: str
    headline: Headline
    change_1w: Change | None = None
    change_13w: Change | None = None
    change_52w: Change | None = None
    components: list[Component] = []
    history: list[Point] = []
    regime: RegimeFlag | None = None
    easy_label: str = Field("", description="Ein Wort fuer den Easy-Modus")
    easy_summary: str = Field("", description="Ein Satz fuer den Easy-Modus, ohne Zahlen")
    source: str
    fetched_at: datetime
    fingerprint: str = Field(description="Aendert sich nur, wenn sich die Daten aendern; Cache-Schluessel fuer Erklaerungen")


ZoneKey = Literal["very_negative", "negative", "neutral", "positive", "very_positive"]
MarketConfirmKey = Literal["confirmed", "market_ahead", "market_lagging"]
MarketConfirmKey = Literal["confirmed", "market_ahead", "market_lagging"]
PhaseKey = Literal["recovery", "expansion", "late", "downturn"]


class ConsensusResponse(BaseModel):
    score: int | None = Field(description="Rang 0 bis 100: besser als X % der Wochen der letzten zehn Jahre")
    composite: float | None = Field(None, description="Rohwert: gewichtetes Mittel der Treiber nach Overlays und Vetos")
    zone_key: ZoneKey
    zone: str
    zone_raw_key: ZoneKey | None = Field(None, description="Zone dieser Woche, falls noch nicht bestaetigt")
    weeks_in_zone: int | None = None
    market_confirmation_key: MarketConfirmKey | None = Field(None, description="Bestaetigt der Marktsignal-Score den Rang?")
    market_confirmation: str | None = None
    phase_key: PhaseKey | None = Field(None, description="Bestaetigte Zyklusphase (Hysterese)")
    phase: str | None = None
    phase_raw_key: PhaseKey | None = Field(None, description="Rohsignal dieser Woche, noch nicht bestaetigt")
    weeks_in_phase: int | None = None
    liquidity_direction: Literal["up", "down"] | None = None
    growth_direction: Literal["up", "down"] | None = None
    confidence: Literal["klar", "knapp"] = "klar"
    method: str
    note: str
    why: str
    pillar_scores: dict[str, int | None]
    overlay_scores: dict[str, int | None] = Field(default_factory=dict)
    core: float | None = None
    mechanics_adjustment: float = 0.0
    valuation_cap: float | None = None
    vetoes: list[str] = Field(default_factory=list)
    cap: float | None = Field(None, description="Wirksamer Deckel (Minimum aus Bewertung und Vetos)")
    adjusted: float | None = Field(None, description="Kern plus Mechanik, vor dem Deckel")


class DashboardResponse(BaseModel):
    consensus: ConsensusResponse
    pillars: list[PillarResponse] = Field(description="Die vier Treiber-Saeulen")
    overlays: list[PillarResponse] = Field(default_factory=list, description="Verstaerker und Bremsen: Bewertung, Marktmechanik")
    generated_at: datetime


class ExplanationResponse(BaseModel):
    pillar_id: PillarId
    status: Literal["ready", "unavailable"]
    text: str | None = None
    reason: str | None = None
    provider: Literal["anthropic", "gemini", "ollama", "template"] | None = None
    model: str | None = None
    generated_at: datetime | None = None
    fingerprint: str
    cached: bool = False


class HistoryPoint(BaseModel):
    date: date
    score: int
    level: int
    momentum: int


class ConsensusHistoryPoint(BaseModel):
    date: date
    score: int = Field(description="Rang 0 bis 100")
    composite: int = Field(description="Rohwert vor der Rangnormierung")
    zone_key: ZoneKey = Field(description="Bestaetigte Zone")
    zone_raw_key: ZoneKey
    phase_key: PhaseKey
    phase_raw_key: PhaseKey
    liquidity_direction: Literal["up", "down"]
    growth_direction: Literal["up", "down"]


class HistoryResponse(BaseModel):
    start: date
    end: date
    frequency: Literal["weekly"] = "weekly"
    pillars: dict[str, list[HistoryPoint]]
    consensus: list[ConsensusHistoryPoint]
    generated_at: datetime
