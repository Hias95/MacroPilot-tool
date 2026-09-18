/** Zahlen- und Datumsformatierung, deutsch (de-DE). */

import type { Change, Frequency, ValueFormat } from "./api";

const de = (digits: number) =>
  new Intl.NumberFormat("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const de0 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });

const MINUS = "−";
const sign = (n: number) => (n > 0 ? "+" : n < 0 ? MINUS : "");

/** FRED liefert Mio. USD. 6.712.345 Mio. -> "6,71 Bio. $" (deutsche Billion = 10^12). */
export function formatMillionsUsd(millions: number): string {
  const abs = Math.abs(millions);
  const neg = millions < 0 ? MINUS : "";
  if (abs >= 1_000_000) return `${neg}${de(2).format(abs / 1_000_000)} Bio. $`;
  if (abs >= 1_000) return `${neg}${de(1).format(abs / 1_000)} Mrd. $`;
  return `${neg}${de0.format(abs)} Mio. $`;
}

export function formatSignedMillionsUsd(millions: number): string {
  return `${sign(millions)}${formatMillionsUsd(Math.abs(millions))}`;
}

export function formatSignedPct(pct: number, digits = 2): string {
  return `${sign(pct)}${de(digits).format(Math.abs(pct))} %`;
}

/** Hauptwert je nach Datenart. */
export function formatValue(value: number, format: ValueFormat): string {
  switch (format) {
    case "usd_millions":
      return formatMillionsUsd(value);
    case "index":
      return de(1).format(value);
    case "diffusion":
      return `${sign(value)}${de(1).format(Math.abs(value))}`;
    case "ratio":
      return de(3).format(value);
    case "percent":
      return `${value < 0 ? MINUS : ""}${de(2).format(Math.abs(value))} %`;
    case "pp":
      return `${sign(value)}${de(2).format(Math.abs(value))} Pp.`;
    case "price":
      return de(2).format(value);
  }
}

/** Zeitraum-Label: woechentliche Serien in Wochen, monatliche in Monaten. */
export function formatSpan(weeks: number, frequency: Frequency = "weekly"): string {
  return frequency === "monthly" ? `${Math.round(weeks / 4.345)} M` : `${weeks} W`;
}

/** Veraenderung je nach Datenart, kompakt fuer den Delta-Chip. */
export function formatChange(change: Change, format: ValueFormat, frequency: Frequency = "weekly"): string {
  const span = formatSpan(change.weeks, frequency);
  switch (format) {
    case "usd_millions":
      return `${formatSignedPct(change.pct)} / ${span}`;
    case "index":
    case "diffusion":
      return `${sign(change.abs)}${de(1).format(Math.abs(change.abs))} Pkt. / ${span}`;
    case "ratio":
    case "price":
      return `${formatSignedPct(change.pct, 1)} / ${span}`;
    case "percent":
    case "pp":
      return `${sign(change.abs)}${de(2).format(Math.abs(change.abs))} Pp. / ${span}`;
  }
}

export function formatDateDe(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }).format(d);
}

/** Datenstand: Tagesdatum bei woechentlichen Serien, Monatsname bei monatlichen. */
export function formatPeriod(iso: string, frequency: Frequency = "weekly"): string {
  if (frequency !== "monthly") return formatDateDe(iso);
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("de-DE", { month: "long", year: "numeric" }).format(d);
}

export function formatDateTimeDe(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

/**
 * Zeitpunkt des Seitenaufrufs, einmal beim Laden festgehalten.
 *
 * Das Alter einer Kennzahl direkt aus Date.now() zu rechnen, macht das Rendern unrein (eslint
 * react-hooks/purity) und kann bei zwei Renderdurchlaeufen zwei verschiedene Werte liefern. Ein fester
 * Bezugspunkt pro Seitenaufruf ist genau genug: Die Seite wird taeglich neu gebaut.
 */
const LOADED_AT = Date.now();

/**
 * Alter in ganzen Tagen, nie negativ. Abgerundet, nicht gerundet: Eine Zahl vom 1. ist am 18. siebzehn Tage
 * alt, nicht achtzehn. Aufrunden haette das Alter am Nachmittag um einen Tag ueberschaetzt.
 */
export function ageInDays(iso: string): number {
  return Math.max(0, Math.floor((LOADED_AT - new Date(iso).getTime()) / 86_400_000));
}

/** Alter in Alltagsworten: "von heute", "1 Tag alt", "9 Tage alt". */
export function ageText(iso: string): string {
  const days = ageInDays(iso);
  if (days === 0) return "von heute";
  if (days === 1) return "1 Tag alt";
  return `${days} Tage alt`;
}

/**
 * Zahl mit deutschem Dezimalkomma. In den zuletzt gebauten Bausteinen stand "+11.3 Punkte" neben
 * "+17,4 Pkt." aus der aelteren Formatierung; das sah nach Maschine aus statt nach Sorgfalt.
 */
export function formatDe(value: number, digits = 1, sign = false): string {
  const text = value.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return sign && value > 0 ? `+${text}` : text;
}
