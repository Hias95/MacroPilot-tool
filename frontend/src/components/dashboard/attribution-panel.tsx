"use client";

import { TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { ConsensusResponse, HistoryResponse, PillarResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

const WEEKS = 13;

/**
 * C3: Welcher Treiber hat den Score bewegt?
 *
 * Der Beitrag einer Säule zum Rohwert ist ihr Score mal ihrem Gewicht. Die Veränderung dieses Beitrags über
 * dreizehn Wochen sagt, wer den Gesamtwert getragen und wer ihn gebremst hat. Das steht sonst nirgends: Die
 * Kacheln zeigen jede Säule für sich, aber nicht ihren Anteil an der Bewegung.
 */
export function AttributionPanel({ consensus, pillars, history }: { consensus: ConsensusResponse; pillars: PillarResponse[]; history: HistoryResponse | null }) {
  const nameOf = (id: string) => pillars.find((p) => p.id === id)?.name ?? id;
  const weights = consensus.weights;
  if (!history || !weights || Object.keys(weights).length === 0) return null;

  const moves = Object.entries(weights)
    .map(([id, weight]) => {
      const points = history.pillars[id] ?? [];
      if (points.length <= WEEKS) return null;
      const now = points[points.length - 1];
      const then = points[points.length - 1 - WEEKS];
      return { id, name: nameOf(id), delta: weight * (now.score - then.score) };
    })
    .filter((m): m is NonNullable<typeof m> => m != null);
  if (moves.length === 0) return null;

  const total = moves.reduce((sum, m) => sum + m.delta, 0);
  const max = Math.max(...moves.map((m) => Math.abs(m.delta)), 0.5);
  const sorted = [...moves].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <TrendingUp className="size-3.5" />
            Wer hat den Rohwert bewegt? Letzte {WEEKS} Wochen
          </h2>
          <span className="text-[11px] tabular-nums text-muted-foreground/80">
            zusammen {total >= 0 ? "+" : ""}{total.toFixed(1)} Punkte
          </span>
        </div>
        <ul className="flex flex-col gap-1.5">
          {sorted.map((m) => {
            const up = m.delta >= 0;
            return (
              <li key={m.id} className="grid grid-cols-[8rem_1fr_4.5rem] items-center gap-3 text-sm">
                <span className="truncate">{m.name}</span>
                {/* Balken von der Mitte aus: links bremsend, rechts stützend. */}
                <span className="relative flex h-2 items-center" aria-hidden>
                  <span className="absolute inset-y-0 left-1/2 w-px bg-white/15" />
                  <span
                    className={cn("absolute h-1.5 rounded-full", up ? "bg-emerald-400/80" : "bg-rose-400/80")}
                    style={{
                      width: `${(Math.abs(m.delta) / max) * 48}%`,
                      left: up ? "50%" : undefined,
                      right: up ? undefined : "50%",
                    }}
                  />
                </span>
                <span className={cn("text-right tabular-nums", up ? "text-emerald-300" : "text-rose-300")}>
                  {up ? "+" : ""}{m.delta.toFixed(1)}
                </span>
              </li>
            );
          })}
        </ul>
        <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
          Beitrag heißt Score mal Gewicht. Eine Säule kann sich also stark bewegen und trotzdem wenig ausmachen,
          wenn ihr Gewicht klein ist. Die Summe ist die Veränderung des Rohwerts vor Overlays und Deckel.
        </p>
      </CardContent>
    </Card>
  );
}
