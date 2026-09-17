import { fetchBacktest, type BacktestBand, type BacktestResponse, type BacktestVariant, type ZoneKey } from "./api";

/** Der Backtest ist eine grosse Datei und wird von zwei Panels gebraucht. Einmal laden, beide bedienen. */
let pending: Promise<BacktestResponse> | null = null;

export function loadBacktest(): Promise<BacktestResponse> {
  if (!pending) {
    pending = fetchBacktest().catch((err: unknown) => {
      pending = null; // ein Fehlschlag darf den naechsten Versuch nicht blockieren
      throw err;
    });
  }
  return pending;
}

/** Die Variante, die auch live laeuft: Rang ueber zehn Jahre. Sonst die erste. */
export function liveVariant(data: BacktestResponse): BacktestVariant | null {
  if (!data.variants?.length) return null;
  return data.variants.find((v) => v.name.toLowerCase().includes("live")) ?? data.variants[0];
}

export function bandFor(variant: BacktestVariant, zone: ZoneKey): BacktestBand | null {
  return variant.bands.find((b) => b.key === zone) ?? null;
}

/** Unter dieser Zahl getrennter Phasen ist die Zone zu duenn belegt, um sie ohne Vorbehalt zu zeigen. */
export const THIN_EVIDENCE_EPISODES = 10;

/** Der Horizont, auf den sich der Erwartungssatz bezieht. Das Modell ist auf 13 bis 26 Wochen am staerksten. */
export const OUTLOOK_WEEKS = 13;
export const OUTLOOK_LABEL = "drei Monate";
