"use client";

import { Scale } from "lucide-react";
import type { ConsensusResponse } from "@/lib/api";
import { formatDe } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * J2: Woran erkenne ich, dass es kippt?
 *
 * Der angezeigte Rang ist ein Perzentil. Um die nächste Zonengrenze zu erreichen, muss der Rohwert auf den
 * Wert steigen, der dort im Vergleichsfenster liegt. Geteilt durch das Gewicht eines Treibers ergibt das:
 * So viele Punkte müsste allein dieser Treiber zulegen, wenn sich sonst nichts bewegt. Das macht die
 * Gewichtung zum ersten Mal erfahrbar, statt sie nur zu behaupten.
 */
export function TippingNote({ consensus, compact = false }: { consensus: ConsensusResponse; compact?: boolean }) {
  const rows = consensus.tipping ?? [];
  if (rows.length === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      <h3 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        <Scale className="size-3.5" />
        Woran du merkst, dass es kippt
      </h3>
      <ul className="flex flex-col gap-1.5 text-sm">
        {rows.map((t) => {
          const easiest = [...t.drivers].sort((a, b) => Math.abs(a.points) - Math.abs(b.points))[0];
          const up = t.direction === "up";
          return (
            <li key={t.boundary} className="text-pretty">
              <span className={cn("font-medium", up ? "text-emerald-300" : "text-rose-300")}>
                Bis {t.label}
              </span>{" "}
              <span className="text-muted-foreground">
                fehlen {t.rank_gap} Ränge. Das entspricht {formatDe(Math.abs(t.value_gap), 1)} Punkten im Rohwert, oder{" "}
                {easiest ? (
                  <>
                    allein {easiest.name} {up ? "plus" : "minus"}{" "}
                    <span className="tabular-nums">{formatDe(Math.abs(easiest.points), 1)}</span> Punkte
                  </>
                ) : null}
                , wenn sich sonst nichts bewegt.
              </span>
            </li>
          );
        })}
      </ul>
      {!compact ? (
        <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
          Gerechnet je Treiber einzeln. In Wirklichkeit bewegen sich mehrere gleichzeitig, meist gegenläufig. Die Zahl
          zeigt vor allem, wie schwer die einzelnen Treiber wiegen: Was bei einem acht Punkte braucht, braucht beim
          leichtesten Treiber ein Vielfaches.
        </p>
      ) : null}
    </div>
  );
}
