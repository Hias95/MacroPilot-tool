"use client";

import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import type { HistoryPoint } from "@/lib/api";
import { formatDateDe } from "@/lib/format";

interface Props {
  points: HistoryPoint[];
  accent: string;
  height?: number;
}

/** Verlauf eines Scores (0 bis 100) ueber die letzten Wochen, mit Mittellinie bei 50. */
export function ScoreSparkline({ points, accent, height = 56 }: Props) {
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 4, right: 2, bottom: 2, left: 2 }}>
          <YAxis hide domain={[0, 100]} />
          <ReferenceLine y={50} stroke="oklch(1 0 0 / 15%)" strokeDasharray="2 3" />
          <Tooltip
            cursor={{ stroke: accent, strokeOpacity: 0.4 }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as HistoryPoint | undefined;
              if (!active || !p) return null;
              return (
                <div className="rounded-md border border-border bg-popover px-2 py-1 text-[11px] shadow-lg">
                  <span className="text-muted-foreground">{formatDateDe(p.date)}</span> <span className="font-mono tabular-nums">{p.score}</span>
                </div>
              );
            }}
          />
          <Line type="monotone" dataKey="score" stroke={accent} strokeWidth={1.75} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
