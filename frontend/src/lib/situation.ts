"use client";

import { useSyncExternalStore } from "react";

/**
 * I1: Die eigene Lage des Lesers.
 *
 * Ein Tacho mit Ampelfarben fragt unausgesprochen "ist jetzt ein guter Zeitpunkt". Für jemanden mit einem
 * monatlichen Sparplan ist das die falsche Frage, denn der einzelne Zeitpunkt betrifft nur einen kleinen
 * Teil seiner Summe. Dieselben Daten bedeuten je nach Lage etwas anderes. Gespeichert wird nur die Auswahl,
 * die Daten bleiben identisch.
 */
export type Situation = "plan" | "lump" | "invested";

const KEY = "macropilot.situation";
const listeners = new Set<() => void>();

function read(): Situation {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw === "lump" || raw === "invested" ? raw : "plan";
  } catch {
    return "plan";
  }
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  window.addEventListener("storage", callback);
  return () => {
    listeners.delete(callback);
    window.removeEventListener("storage", callback);
  };
}

export function useSituation(): Situation {
  return useSyncExternalStore(subscribe, read, () => "plan");
}

export function setSituation(value: Situation) {
  try {
    window.localStorage.setItem(KEY, value);
  } catch {
    /* privates Fenster o. ae. */
  }
  listeners.forEach((l) => l());
}

export const SITUATIONS: { key: Situation; label: string; short: string }[] = [
  { key: "plan", label: "Ich spare monatlich", short: "Sparplan" },
  { key: "lump", label: "Ich will eine größere Summe anlegen", short: "Größere Summe" },
  { key: "invested", label: "Ich bin bereits investiert", short: "Bereits investiert" },
];
