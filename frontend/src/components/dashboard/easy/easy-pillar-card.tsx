"use client";

import { useState } from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight, ChevronDown, Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { HistoryPoint, PillarResponse } from "@/lib/api";
import { PILLAR_UI } from "@/lib/pillars";
import { filterByRange, type RangeKey } from "@/lib/range";
import { cn } from "@/lib/utils";
import { ScoreSparkline } from "./score-sparkline";

interface Props {
  pillar: PillarResponse;
  /** Wochen-Scores, aelteste zuerst; gezeigt wird der gewaehlte Zeithorizont */
  points: HistoryPoint[];
  range?: RangeKey;
  compact?: boolean;
}

export function ampelColor(score: number | null): string {
  if (score == null) return "oklch(0.6 0.02 260)";
  if (score >= 60) return "oklch(0.78 0.18 150)";
  if (score < 40) return "oklch(0.7 0.19 25)";
  return "oklch(0.82 0.16 75)";
}

function trendOf(points: HistoryPoint[]): { dir: "up" | "flat" | "down"; delta: number } {
  if (points.length < 5) return { dir: "flat", delta: 0 };
  const delta = points[points.length - 1].score - points[points.length - 5].score;
  return { dir: delta >= 5 ? "up" : delta <= -5 ? "down" : "flat", delta };
}

export function EasyPillarCard({ pillar, points, range = "6m", compact = false }: Props) {
  const ui = PILLAR_UI[pillar.id];
  const score = pillar.score?.score ?? null;
  const recent = filterByRange(points, range);
  const trend = trendOf(points);
  const color = ampelColor(score);
  const [open, setOpen] = useState(false);
  const TrendIcon = trend.dir === "up" ? ArrowUpRight : trend.dir === "down" ? ArrowDownRight : ArrowRight;

  return (
    <Card className="relative bg-card ring-white/8">
      <span aria-hidden className="pointer-events-none absolute inset-x-6 top-0 h-px" style={{ background: `linear-gradient(90deg, transparent, ${ui.accent}, transparent)` }} />
      {/* flex-1 laesst den Inhalt die Kartenhoehe fuellen, erst dann greift das mt-auto am Link. */}
      <CardContent className="flex flex-1 flex-col gap-3 py-1">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="size-2 shrink-0 rounded-full" style={{ background: ui.accent }} />
              <h3 className="font-heading truncate text-base font-semibold tracking-tight">{pillar.name}</h3>
            </div>
            {!compact ? <p className="mt-0.5 text-xs text-muted-foreground text-pretty">{pillar.measures}</p> : null}
          </div>
          <span
            className={cn("inline-flex shrink-0 items-center gap-0.5 rounded-md px-1.5 py-0.5 text-[11px] font-medium", trend.dir === "up" && "text-emerald-300", trend.dir === "down" && "text-rose-300", trend.dir === "flat" && "text-muted-foreground")}
            title={`Veränderung des Scores über 4 Wochen: ${trend.delta >= 0 ? "+" : ""}${trend.delta}`}
          >
            <TrendIcon className="size-3.5" />
            4 W
          </span>
        </div>

        <div className="flex items-baseline gap-3">
          <span className="font-heading text-4xl font-semibold tracking-tight tabular-nums leading-none" style={{ color }}>
            {score ?? "—"}
          </span>
          <span className="inline-flex items-center gap-1.5 text-sm font-medium">
            <span className="size-2.5 rounded-full" style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
            {pillar.easy_label}
          </span>
        </div>

        {recent.length > 1 ? <ScoreSparkline points={recent} accent={ui.accent} /> : <div className="h-14 text-[11px] text-muted-foreground">Verlauf folgt, sobald genug Wochen vorliegen.</div>}

        <div className="flex flex-col gap-1.5">
          <p className="text-sm leading-relaxed text-foreground/90 text-pretty">{pillar.easy_summary}</p>
          {pillar.easy_drivers ? (
            <p className="text-sm leading-relaxed text-muted-foreground text-pretty">{pillar.easy_drivers}</p>
          ) : null}
          {pillar.easy_role ? (
            <p className="text-[11px] leading-relaxed text-muted-foreground/70 text-pretty">{pillar.easy_role}</p>
          ) : null}
        </div>

        {/* mt-auto haelt den Link am unteren Rand, damit unterschiedlich lange Texte das Raster nicht verrutschen. */}
        <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="mt-auto inline-flex w-fit items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground">
          <Info className="size-3" />
          Was steckt dahinter?
          <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
        </button>
        {open ? (
          <div className="rounded-lg border border-border/60 bg-white/[0.02] p-3 text-xs leading-relaxed text-muted-foreground">
            <p className="text-pretty">{ui.explainer}</p>
            <p className="mt-2 text-pretty text-foreground/80">{ui.reading}</p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
