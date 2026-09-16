"use client";

import { useCallback, useSyncExternalStore } from "react";

/** Zeithorizont fuer Verlaufs-Charts. Gemerkt je Chart im Browser. */
export type RangeKey = "6m" | "1y" | "3y" | "5y" | "10y" | "max";

export const RANGES: { key: RangeKey; label: string; months: number | null }[] = [
  { key: "6m", label: "6 M", months: 6 },
  { key: "1y", label: "1 J", months: 12 },
  { key: "3y", label: "3 J", months: 36 },
  { key: "5y", label: "5 J", months: 60 },
  { key: "10y", label: "10 J", months: 120 },
  { key: "max", label: "Max", months: null },
];

const KEYS = new Set<string>(RANGES.map((r) => r.key));

/** Behaelt die Punkte ab (letztes Datum minus Monate). Erwartet aufsteigend sortierte ISO-Daten. */
export function filterByRange<T extends { date: string }>(points: T[], range: RangeKey): T[] {
  const months = RANGES.find((r) => r.key === range)?.months ?? null;
  if (months == null || points.length === 0) return points;
  const last = new Date(points[points.length - 1].date);
  const cutoff = new Date(Date.UTC(last.getUTCFullYear(), last.getUTCMonth() - months, last.getUTCDate()));
  const iso = cutoff.toISOString().slice(0, 10);
  const idx = points.findIndex((p) => p.date >= iso);
  return idx <= 0 ? points : points.slice(idx);
}

/** Welche Horizonte bei dieser Punktzahl ueberhaupt Sinn ergeben (kuerzer als die Daten oder Max). */
export function availableRanges(points: { date: string }[]): RangeKey[] {
  if (points.length < 2) return ["max"];
  const first = new Date(points[0].date);
  const last = new Date(points[points.length - 1].date);
  const spanMonths = (last.getTime() - first.getTime()) / (1000 * 60 * 60 * 24 * 30.44);
  return RANGES.filter((r) => r.months == null || r.months < spanMonths).map((r) => r.key);
}

const listeners = new Set<() => void>();

function subscribe(callback: () => void) {
  listeners.add(callback);
  window.addEventListener("storage", callback);
  return () => {
    listeners.delete(callback);
    window.removeEventListener("storage", callback);
  };
}

/** Gemerkter Horizont je Chart (localStorage). Auf dem Server und beim ersten Rendern immer der Standard. */
export function useRange(id: string, fallback: RangeKey): [RangeKey, (r: RangeKey) => void] {
  const storageKey = `macropilot.range.${id}`;
  const range = useSyncExternalStore(
    subscribe,
    () => {
      try {
        const stored = window.localStorage.getItem(storageKey);
        return stored && KEYS.has(stored) ? (stored as RangeKey) : fallback;
      } catch {
        return fallback;
      }
    },
    () => fallback,
  );
  const setRange = useCallback(
    (r: RangeKey) => {
      try {
        window.localStorage.setItem(storageKey, r);
      } catch {
        /* privates Fenster o. ae. */
      }
      listeners.forEach((l) => l());
    },
    [storageKey],
  );
  return [range, setRange];
}
