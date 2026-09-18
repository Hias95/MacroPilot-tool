/** Typisierter Client fuer die MacroPilot-API. Typen spiegeln backend/app/schemas.py. */

export type PillarId = "liquidity" | "cycle" | "markets" | "structure" | "mechanics" | "valuation";
export type PillarKind = "driver" | "overlay";
export type PillarStatus = "live" | "demo";
export type Tone = "bearish" | "neutral" | "bullish";
export type ValueFormat = "usd_millions" | "index" | "diffusion" | "ratio" | "percent" | "pp" | "price";
export type Frequency = "weekly" | "monthly";
export type ZoneKey = "very_negative" | "negative" | "neutral" | "positive" | "very_positive";
export type MarketConfirmKey = "confirmed" | "market_ahead" | "market_lagging";
export type PhaseKey = "recovery" | "expansion" | "late" | "downturn";
export type ExplanationProvider = "anthropic" | "gemini" | "ollama" | "template";

export interface Point {
  date: string; // ISO yyyy-mm-dd
  value: number;
}

export interface Change {
  weeks: number;
  abs: number;
  pct: number;
}

export interface ScoreBreakdown {
  score: number;
  level: number;
  momentum: number;
  level_weight: number;
  momentum_window: number;
  lookback: number;
  unit: "weeks" | "months" | "quarters";
  method: string;
  /** Veraenderung der Basis-Serie ueber momentum_window (Prozent oder absolut). */
  change?: number | null;
}

export interface Headline {
  label: string;
  value: number;
  unit: string;
  format: ValueFormat;
  date: string;
  /** Ist ein steigender Wert gut (+) oder schlecht (-) fuer den Score */
  sign: "+" | "-";
}

export interface Component {
  id: string;
  label: string;
  value: number;
  unit: string;
  format: ValueFormat;
  date: string;
  sign: "+" | "-";
  change_13w_pct: number | null;
  change_13w_abs: number | null;
  score: number | null;
  note: string | null;
}

export interface RegimeCriterion {
  label: string;
  value_text: string;
  met: boolean;
}

export interface RegimeFlag {
  id: string;
  label: string;
  active: boolean;
  met_count: number;
  needed: number;
  criteria: RegimeCriterion[];
  hint: string;
}

export interface PillarResponse {
  id: PillarId;
  name: string;
  measures: string;
  legend: string;
  status: PillarStatus;
  kind: PillarKind;
  frequency: Frequency;
  tone: Tone;
  score: ScoreBreakdown | null;
  score_note: string;
  headline: Headline;
  change_1w: Change | null;
  change_13w: Change | null;
  change_52w: Change | null;
  components: Component[];
  history: Point[];
  regime: RegimeFlag | null;
  easy_label: string;
  easy_summary: string;
  /** Welcher Bestandteil die Saeule gerade traegt und welcher sie bremst. */
  easy_drivers?: string;
  /** Was die Saeule im Gesamtscore bewirkt: Gewicht bei Treibern, Aufgabe bei Overlays. */
  easy_role?: string;
  source: string;
  fetched_at: string;
  fingerprint: string;
}

export interface ConsensusResponse {
  /** Rang des Rohwerts in den letzten zehn Jahren (0 bis 100). */
  score: number | null;
  /** Rohwert des Modells vor der Rangbildung. */
  composite: number | null;
  zone_key: ZoneKey;
  zone: string;
  /** Zone der aktuellen Woche, noch ohne Bestaetigung. */
  zone_raw_key: ZoneKey;
  weeks_in_zone: number | null;
  /** Zone, die auf Bestaetigung wartet; null, wenn nichts schwebt. */
  zone_pending_key?: ZoneKey | null;
  zone_pending_weeks?: number;
  zone_confirm_weeks?: number;
  /** Tag, an dem der Wechsel bestaetigt waere, wenn die Zone bestehen bleibt. */
  zone_change_date?: string | null;
  /** Bestaetigt der Marktsignal-Score den Rang? */
  market_confirmation_key: MarketConfirmKey | null;
  market_confirmation: string | null;
  phase_key: PhaseKey | null;
  phase: string | null;
  phase_raw_key: PhaseKey | null;
  weeks_in_phase: number | null;
  liquidity_direction: "up" | "down" | null;
  /** Abgestufte Kurzform derselben Bewegung, z. B. "kaum verändert". Verhindert, dass Badge und Text auseinanderlaufen. */
  liquidity_move?: string | null;
  growth_move?: string | null;
  growth_direction: "up" | "down" | null;
  confidence: "klar" | "knapp";
  method: string;
  note: string;
  why: string;
  /** Rangfolge der widersprechenden Hinweise: Zeitpunkt gegen Fallhöhe. */
  weighting?: string;
  pillar_scores: Record<string, number | null>;
  /** Gewicht je Treiber im Kern, Summe 1. Grundlage der Beitragsrechnung. */
  weights?: Record<string, number>;
  overlay_scores: Record<string, number | null>;
  core: number | null;
  mechanics_adjustment: number;
  valuation_cap: number | null;
  vetoes: string[];
  cap: number | null;
  /** Greift der Deckel gerade wirklich, senkt er den Wert also? */
  cap_binding?: boolean;
  adjusted: number | null;
}

export interface DashboardResponse {
  consensus: ConsensusResponse;
  pillars: PillarResponse[];
  overlays: PillarResponse[];
  generated_at: string;
}

export interface ExplanationResponse {
  pillar_id: PillarId;
  status: "ready" | "unavailable";
  text: string | null;
  reason: string | null;
  provider: ExplanationProvider | null;
  model: string | null;
  generated_at: string | null;
  fingerprint: string;
  cached: boolean;
}

export interface HistoryPoint {
  date: string;
  score: number;
  level: number;
  momentum: number;
}

export interface ConsensusHistoryPoint {
  date: string;
  /** Rang des Rohwerts in den vorangegangenen zehn Jahren. */
  score: number;
  composite: number;
  zone_key: ZoneKey;
  zone_raw_key: ZoneKey;
  phase_key: PhaseKey;
  phase_raw_key: PhaseKey;
  liquidity_direction: "up" | "down";
  growth_direction: "up" | "down";
}

export interface HistoryResponse {
  start: string;
  end: string;
  frequency: "weekly";
  pillars: Record<string, HistoryPoint[]>;
  consensus: ConsensusHistoryPoint[];
  generated_at: string;
}

export interface HealthResponse {
  status: string;
  fred_api_key_configured: boolean;
  anthropic_api_key_configured: boolean;
  gemini_api_key_configured: boolean;
  explain_provider: ExplanationProvider | "none";
  explain_model: string | null;
  cache_ttl_seconds: number;
  last_refresh?: string | null;
  snapshot_date?: string | null;
  auto_refresh?: boolean;
  alert_channels?: string[];
  /** Aeltester Eingang ueber alle Saeulen. Der Gesamtscore mischt Daten unterschiedlichen Alters. */
  oldest_input?: string | null;
  recording_since?: string | null;
  /** Was das Modell ueber sich selbst sagt: Version, Parameter, Konzentration, Vergleichsfenster. */
  model?: ModelCard;
  mode?: "static";
  generated_at?: string;
}

/** Anteil einer Einzelserie am Gesamtscore. */
export interface ConcentrationRow {
  pillar: string;
  pillar_label: string;
  label: string;
  share: number;
}
export interface ModelCard {
  version: string;
  parameters_hash: string;
  weights: Record<string, number>;
  rank_window_weeks: number;
  rank_min_history_weeks: number;
  zone_confirm_weeks: number;
  concentration: ConcentrationRow[];
  /** Zusammen: wie viel des Scores an Notenbankbilanzen haengt. */
  central_bank_share: number;
}

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
/** static = JSON-Dateien aus dem taeglichen Export (GitHub Actions) statt einer laufenden API. */
export const DATA_MODE: "api" | "static" = process.env.NEXT_PUBLIC_DATA_MODE === "static" ? "static" : "api";
export const DATA_URL = `${(process.env.NEXT_PUBLIC_BASE_PATH ?? "").replace(/\/$/, "")}${(process.env.NEXT_PUBLIC_DATA_URL ?? "/data").replace(/\/$/, "")}`;

/** Welche Datei im statischen Modus zu einem API-Pfad gehoert, und welcher Teil davon. */
function staticTarget(path: string): { file: string; pick?: (body: unknown) => unknown } {
  const clean = path.split("?")[0];
  if (clean === "/health") return { file: "meta.json" };
  if (clean === "/api/v1/dashboard") return { file: "dashboard.json" };
  if (clean === "/api/v1/history") return { file: "history.json" };
  if (clean === "/api/v1/backtest") return { file: "backtest.json" };
  if (clean === "/api/v1/changes") return { file: "changes.json" };
  if (clean === "/api/v1/snapshots") return { file: "snapshots.json" };
  if (clean === "/api/v1/data-quality") return { file: "data-quality.json" };
  const explanation = clean.match(/^\/api\/v1\/pillars\/([a-z]+)\/explanation$/);
  if (explanation) {
    const id = explanation[1];
    return {
      file: "explanations.json",
      pick: (body) => {
        const entry = (body as Record<string, unknown>)[id];
        if (!entry) throw new ApiError("Keine Erklärung im Export.", 404);
        return entry;
      },
    };
  }
  const pillar = clean.match(/^\/api\/v1\/pillars\/([a-z]+)$/);
  if (pillar) {
    const id = pillar[1];
    return {
      file: "dashboard.json",
      pick: (body) => {
        const d = body as DashboardResponse;
        const found = [...d.pillars, ...d.overlays].find((p) => p.id === id);
        if (!found) throw new ApiError("Säule nicht im Export.", 404);
        return found;
      },
    };
  }
  throw new ApiError(`Kein statischer Export für ${clean}.`, 404);
}

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (DATA_MODE === "static") {
    const target = staticTarget(path);
    let response: Response;
    try {
      response = await fetch(`${DATA_URL}/${target.file}`, { signal, cache: "no-store" });
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") throw err;
      throw new ApiError(`Daten nicht erreichbar (${DATA_URL}/${target.file}).`);
    }
    if (!response.ok) throw new ApiError(`Datei ${target.file} fehlt (HTTP ${response.status}). Lief der Export?`, response.status);
    const body = (await response.json()) as unknown;
    return (target.pick ? target.pick(body) : body) as T;
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { signal, cache: "no-store" });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(`Backend nicht erreichbar (${API_BASE}). Läuft uvicorn?`);
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* Body war kein JSON */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const fetchDashboard = (signal?: AbortSignal) => request<DashboardResponse>("/api/v1/dashboard", signal);
export const fetchPillar = (id: PillarId, signal?: AbortSignal) => request<PillarResponse>(`/api/v1/pillars/${id}`, signal);
export const fetchExplanation = (id: PillarId, signal?: AbortSignal) =>
  request<ExplanationResponse>(`/api/v1/pillars/${id}/explanation`, signal);
export const fetchHealth = (signal?: AbortSignal) => request<HealthResponse>("/health", signal);
export const fetchHistory = (years: number, signal?: AbortSignal) =>
  request<HistoryResponse>(`/api/v1/history?years=${years}`, signal);

export interface ChangeEvent {
  id: number;
  at: string;
  date: string;
  kind: "zone" | "phase" | "regime" | "confirmation" | "veto";
  key: string;
  from: string | null;
  to: string | null;
  title: string;
  detail: string;
  notified: boolean;
}
export interface ChangesResponse {
  days: number;
  events: ChangeEvent[];
  last_refresh: string | null;
  snapshot_date: string | null;
  /** Tag des aeltesten Tagesbilds: Seit wann wird ueberhaupt aufgezeichnet? */
  recording_since?: string | null;
}
export const fetchChanges = (days: number, signal?: AbortSignal) => request<ChangesResponse>(`/api/v1/changes?days=${days}`, signal);

/** Backtest (C1): wie sich der Consensus seit 2010 zum Vergleichsindex verhalten hat. Reine Historie. */
export interface BacktestBand {
  key: ZoneKey;
  label: string;
  weeks: number;
  share_pct: number;
  /** Mittlere Rendite des Vergleichsindex in den 13 bzw. 52 Wochen nach einer Woche in dieser Zone, in Prozent. */
  mean_fwd_13w: number;
  mean_fwd_52w: number;
  /** Anteil der Faelle mit positiver 13-Wochen-Rendite, in Prozent. */
  hit_rate_13w: number;
  /** Spannweite der 13-Wochen-Rendite: schlechtestes Zehntel, Mitte, bestes Zehntel. */
  p10_fwd_13w: number | null;
  p50_fwd_13w: number | null;
  p90_fwd_13w: number | null;
  /** Zusammenhaengende Aufenthalte in der Zone. Ehrlicheres Mass als die Zahl der Wochen, weil die sich ueberlappen. */
  episodes: number;
  n_13w: number;
  /** Praktisch unabhaengige Faelle und das 95-Prozent-Intervall der Trefferquote (Wilson). */
  n_effective?: number;
  hit_low_13w?: number | null;
  hit_high_13w?: number | null;
}
export interface BacktestPerformance {
  cagr_pct: number;
  vol_pct: number;
  sharpe: number;
  max_drawdown_pct: number;
  /** Mittlere Investitionsquote der Regel, 1 = immer voll investiert. */
  avg_exposure: number;
  band_changes_per_year: number;
  yearly: Record<string, number>;
}
export interface BacktestVariant {
  name: string;
  start: string;
  end: string;
  weeks: number;
  /** Rangkorrelation zum Vorwaertsertrag je Horizont in Wochen. */
  ic: Record<string, number>;
  bands: BacktestBand[];
  distribution: { min: number; p10: number; p50: number; p90: number; max: number; std: number };
  buy_hold: BacktestPerformance;
  /** Defensive Variante (0 bis 100 % investiert) und die Variante mit Grundquote (50 bis 100 %). */
  strategy: BacktestPerformance;
  strategy_base: BacktestPerformance;
}
/** Dieselbe Zone unter einer Zusatzbedingung: Wie ging es aus, als der Markt dabei extrem teuer war? */
export interface ConditionalBand {
  zone: ZoneKey;
  condition: "valuation_extreme" | "valuation_other" | "market_confirmed" | "market_other";
  label: string;
  weeks: number;
  /** Betroffene Zonenaufenthalte, nicht zusammenhaengende Abschnitte der Teilmenge. */
  episodes: number;
  n_13w: number;
  hit_rate_13w: number | null;
  mean_fwd_13w: number | null;
  p10_fwd_13w: number | null;
  p50_fwd_13w: number | null;
}

/** Zonen-Kennzahlen einer weiteren Anlage oder eines anderen Zeitfensters. */
export interface BenchmarkBand {
  zone: ZoneKey;
  n_13w: number;
  episodes: number;
  hit_rate_13w: number | null;
  median_13w: number | null;
}
export interface BenchmarkResult {
  key: string;
  name: string;
  start: string;
  bands: BenchmarkBand[];
}

export interface BacktestResponse {
  benchmark: string;
  start: string;
  end: string;
  variants: BacktestVariant[];
  conditional?: ConditionalBand[];
  /** Gold, Anleihen, Mischung: sagt der Consensus auch ausserhalb von US-Aktien etwas? */
  benchmarks?: BenchmarkResult[];
  /** Dieselbe Rechnung nur ausserhalb des Kalibrierzeitraums. */
  test_window?: BenchmarkResult | null;
  generated_at: number;
}
export const fetchBacktest = (signal?: AbortSignal) => request<BacktestResponse>("/api/v1/backtest", signal);
