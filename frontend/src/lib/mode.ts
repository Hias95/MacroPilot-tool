"use client";

import { useSyncExternalStore } from "react";

export type ViewMode = "easy" | "pro";

const KEY = "macropilot.mode";
const listeners = new Set<() => void>();

function read(): ViewMode {
  try {
    return window.localStorage.getItem(KEY) === "pro" ? "pro" : "easy";
  } catch {
    return "easy";
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

/** Gemerkter Anzeigemodus. Auf dem Server und beim ersten Rendern immer "easy". */
export function useViewMode(): ViewMode {
  return useSyncExternalStore(subscribe, read, () => "easy");
}

export function setViewMode(mode: ViewMode) {
  try {
    window.localStorage.setItem(KEY, mode);
  } catch {
    /* privates Fenster o. ae. */
  }
  listeners.forEach((l) => l());
}
