"use client";

import { RANGES, type RangeKey } from "@/lib/range";
import { cn } from "@/lib/utils";

interface Props {
  value: RangeKey;
  onChange: (r: RangeKey) => void;
  /** Nur diese Horizonte anbieten (Standard: alle). */
  available?: RangeKey[];
  className?: string;
  label?: string;
}

/** Segment-Schalter fuer den Zeithorizont eines Charts: 6 M, 1 J, 3 J, 5 J, 10 J, Max. */
export function RangeSelect({ value, onChange, available, className, label = "Zeithorizont" }: Props) {
  const options = available ? RANGES.filter((r) => available.includes(r.key)) : RANGES;
  return (
    <div role="radiogroup" aria-label={label} className={cn("inline-flex items-center gap-0.5 rounded-md border border-border/60 bg-white/[0.02] p-0.5", className)}>
      {options.map((r) => {
        const active = r.key === value;
        return (
          <button
            key={r.key}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(r.key)}
            className={cn(
              "rounded px-1.5 py-0.5 font-mono text-[10px] tabular-nums transition-colors",
              active ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
}
