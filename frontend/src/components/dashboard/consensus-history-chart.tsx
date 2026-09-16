"use client";

import { Area, ComposedChart, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ConsensusHistoryPoint } from "@/lib/api";
import { formatDateDe } from "@/lib/format";
import { PHASES, ZONES } from "@/lib/score";

interface Props {
  data: ConsensusHistoryPoint[];
  height?: number;
}

const BANDS = Object.values(ZONES);

/** Verlauf des Consensus-Rangs als Flaeche, Ampelzonen im Hintergrund. Ungeglaettet, die Zone traegt die Hysterese. */
export function ConsensusHistoryChart({ data, height = 190 }: Props) {
  const years = Array.from(new Set(data.map((p) => p.date.slice(0, 4))));
  const ticks = (years.length <= 3 ? data.filter((_, i) => i % 13 === 0).map((p) => p.date) : years.filter((y, i) => i === 0 || Number(y) % 2 === 0).map((y) => data.find((p) => p.date.startsWith(y))?.date ?? ""));
  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id="consensus-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(0.9 0.02 260)" stopOpacity={0.25} />
              <stop offset="100%" stopColor="oklch(0.9 0.02 260)" stopOpacity={0} />
            </linearGradient>
          </defs>
          {BANDS.map((b) => (
            <ReferenceArea key={b.key} y1={b.min} y2={b.max} fill={b.color} fillOpacity={0.08} strokeOpacity={0} />
          ))}
          <XAxis
            dataKey="date"
            ticks={ticks}
            tickFormatter={(d: string) => (years.length <= 3 ? formatDateDe(d).slice(3) : d.slice(0, 4))}
            tick={{ fontSize: 10, fill: "oklch(0.67 0.015 260)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis domain={[0, 100]} ticks={[0, 10, 30, 70, 90, 100]} tick={{ fontSize: 10, fill: "oklch(0.67 0.015 260)" }} axisLine={false} tickLine={false} />
          <Tooltip
            cursor={{ stroke: "oklch(1 0 0 / 25%)", strokeDasharray: "3 3" }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as ConsensusHistoryPoint | undefined;
              if (!active || !p) return null;
              const zone = ZONES[p.zone_key];
              return (
                <div className="rounded-md border border-border bg-popover px-2.5 py-1.5 text-xs shadow-lg">
                  <div className="text-muted-foreground">{formatDateDe(p.date)}</div>
                  <div className="font-mono text-sm tabular-nums">
                    {p.score} <span style={{ color: zone.color }}>{zone.label}</span>
                    <span className="text-muted-foreground"> · Rohwert {p.composite}</span>
                  </div>
                  <div className="text-muted-foreground">Phase: {PHASES[p.phase_key].label}</div>
                </div>
              );
            }}
          />
          <Area type="monotone" dataKey="score" stroke="oklch(0.93 0.01 260)" strokeWidth={1.5} fill="url(#consensus-fill)" dot={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
