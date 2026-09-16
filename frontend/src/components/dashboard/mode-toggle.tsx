"use client";

import { setViewMode, useViewMode, type ViewMode } from "@/lib/mode";
import { cn } from "@/lib/utils";

const OPTIONS: Array<{ value: ViewMode; label: string; hint: string }> = [
  { value: "easy", label: "Einfach", hint: "Nur Scores, Ampeln und ein Satz je Säule" },
  { value: "pro", label: "Profi", hint: "Alle Kennzahlen, Bestandteile, Rechenweg und Erklärungen" },
];

export function ModeToggle() {
  const mode = useViewMode();
  return (
    <div role="group" aria-label="Anzeigemodus" className="inline-flex rounded-full border border-border/70 bg-white/3 p-0.5 text-[11px]">
      {OPTIONS.map((o) => (
        <button
          key={o.value}
          type="button"
          title={o.hint}
          aria-pressed={mode === o.value}
          onClick={() => setViewMode(o.value)}
          className={cn(
            "rounded-full px-2.5 py-1 font-medium transition-colors",
            mode === o.value ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
