/** Score-Semantik: 0 = maximal Risk-Off, 100 = maximal Risk-On. Der Consensus-Score ist ein Rang: besser als X Prozent der Wochen der letzten zehn Jahre. */

import type { MarketConfirmKey, PhaseKey, Tone, ZoneKey } from "./api";

export interface Zone {
  key: ZoneKey;
  label: string;
  hint: string;
  color: string;
  min: number;
  max: number;
}

/** Ampelstufen des Consensus-Rangs. Grenzen sind Quantile (10/30/70/90), keine Reihenfolge im Zeitverlauf. */
export const ZONES: Record<ZoneKey, Zone> = {
  very_negative: { key: "very_negative", label: "Stark negativ", hint: "Nur in etwa jeder zehnten Woche der letzten zehn Jahre sah es schlechter aus. Stress dominiert; solche Phasen waren historisch oft Wendepunkte, aber mit großen Schwankungen.", color: "oklch(0.66 0.21 25)", min: 0, max: 10 },
  negative: { key: "negative", label: "Negativ", hint: "Schlechter als der Großteil der letzten zehn Jahre. Mehr Kräfte bremsen als stützen.", color: "oklch(0.75 0.17 50)", min: 10, max: 30 },
  neutral: { key: "neutral", label: "Neutral", hint: "Im mittleren Bereich der letzten zehn Jahre. Stützende und bremsende Kräfte halten sich die Waage.", color: "oklch(0.82 0.13 85)", min: 30, max: 70 },
  positive: { key: "positive", label: "Positiv", hint: "Besser als der Großteil der letzten zehn Jahre. Die Mehrheit der Kräfte stützt.", color: "oklch(0.8 0.16 130)", min: 70, max: 90 },
  very_positive: { key: "very_positive", label: "Stark positiv", hint: "Nur in etwa jeder zehnten Woche sah es besser aus. Fast alles stützt; Überhitzung und Bewertung im Blick behalten.", color: "oklch(0.76 0.19 150)", min: 90, max: 100 },
};

export const PHASES: Record<PhaseKey, { label: string; hint: string; order: number }> = {
  recovery: { label: "Erholung", hint: "Liquidität kommt zurück, die Konjunktur hinkt noch. Historisch beginnen hier Erholungen.", order: 0 },
  expansion: { label: "Aufschwung", hint: "Liquidität und Konjunktur ziehen gemeinsam an.", order: 1 },
  late: { label: "Spätzyklus", hint: "Die Konjunktur läuft noch, aber die Liquidität wird knapper.", order: 2 },
  downturn: { label: "Abschwung", hint: "Liquidität und Konjunktur fallen. Auf die Liquiditätswende warten.", order: 3 },
};

/** Marktbestaetigung: Marktsignale gegen den Consensus-Rang. Kein Treiber, sondern ein Risiko-Hinweis. */
export const MARKET_CONFIRM: Record<MarketConfirmKey, { label: string; hint: string; tone: "good" | "warn" | "bad" }> = {
  confirmed: { label: "Markt bestätigt", hint: "Marktsignale und Makrobild zeigen in dieselbe Richtung. Historisch die verlässlichste Konstellation.", tone: "good" },
  market_lagging: { label: "Markt zögert", hint: "Das Makrobild ist besser als das, was der Markt gerade tut. Rendite historisch gleich, Rückschläge häufiger.", tone: "warn" },
  market_ahead: { label: "Markt läuft voraus", hint: "Der Markt ist optimistischer als das Makrobild. Historisch die schwächste Kombination.", tone: "bad" },
};

export function zoneForScore(score: number): Zone {
  const s = clampScore(score);
  return (Object.values(ZONES).find((z) => s < z.max) ?? ZONES.very_positive) as Zone;
}

export function clampScore(n: number): number {
  if (Number.isNaN(n)) return 50;
  return Math.min(100, Math.max(0, Math.round(n)));
}

export const TONE_LABEL: Record<Tone, string> = { bearish: "Risk-Off", neutral: "Neutral", bullish: "Risk-On" };

/** Tendenz einer Veraenderung: leicht positive Werte bleiben neutral. */
export function toneForChange(pct: number | null | undefined, threshold = 0.1): Tone {
  if (pct == null || Number.isNaN(pct)) return "neutral";
  if (pct > threshold) return "bullish";
  if (pct < -threshold) return "bearish";
  return "neutral";
}

/** Zone dieser Woche, solange sie von der bestaetigten abweicht. Sonst null. */
export function pendingZoneOf(c: { zone_key: ZoneKey; zone_pending_key?: ZoneKey | null; zone_raw_key?: ZoneKey }): Zone | null {
  const key = c.zone_pending_key ?? (c.zone_raw_key !== c.zone_key ? c.zone_raw_key : null);
  return key && key !== c.zone_key ? ZONES[key] : null;
}

/**
 * Aus dem Widerspruch "Nadel im gruenen Feld, Wort noch gelb" wird eine Vorschau mit Datum.
 * Ohne Datum vom Backend bleibt der allgemeine Hinweis auf die Bestaetigungsdauer.
 */
export function zoneChangeNote(c: {
  zone_pending_weeks?: number;
  zone_confirm_weeks?: number;
  zone_change_date?: string | null;
}): string {
  const need = c.zone_confirm_weeks ?? 3;
  const date = c.zone_change_date;
  if (!date) return `Die Zone wechselt erst nach ${need} Wochen in Folge.`;
  const when = new Date(date).toLocaleDateString("de-DE", { day: "2-digit", month: "long", year: "numeric" });
  const weeks = c.zone_pending_weeks ?? 1;
  const streak = weeks >= 2 ? `die ${weeks}. Woche in Folge, ` : "";
  return `${streak}bestätigt wäre der Wechsel am ${when}, wenn es so bleibt.`;
}
