"use client";

import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Point } from "@/lib/api";

interface Props {
  data: Point[];
  color: string;
  id: string;
  height?: number;
  /** Wird beim Ueberfahren mit dem aktiven Punkt aufgerufen, beim Verlassen mit null. */
  onHover?: (point: Point | null) => void;
}

/** Verlaufs-Linie ohne Achsen. Interaktiv: Cursor-Linie, aktiver Punkt, Hover-Callback. */
export function Sparkline({ data, color, id, height = 64, onHover }: Props) {
  const gradientId = `spark-${id}`;
  return (
    <div style={{ height }} className="w-full cursor-crosshair" onMouseLeave={() => onHover?.(null)}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 6, right: 2, bottom: 0, left: 2 }}
          onMouseMove={(state) => {
            const raw = state.activeTooltipIndex;
            const idx = typeof raw === "number" ? raw : Number(raw);
            onHover?.(Number.isInteger(idx) && data[idx] ? data[idx] : null);
          }}
          onMouseLeave={() => onHover?.(null)}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" hide />
          <YAxis hide domain={["dataMin", "dataMax"]} />
          <Tooltip
            content={() => null}
            cursor={{ stroke: color, strokeOpacity: 0.5, strokeDasharray: "3 3" }}
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.75}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 3.5, fill: color, stroke: "oklch(0.17 0.009 260)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
