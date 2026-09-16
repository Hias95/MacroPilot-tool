"use client";

import { useState, type CSSProperties, type ReactNode } from "react";
import { ChevronDown, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import type { PillarStatus, Tone } from "@/lib/api";
import { clampScore, TONE_LABEL } from "@/lib/score";
import { cn } from "@/lib/utils";

interface PillarCardProps {
  name: string;
  measures: string;
  legend: string;
  status: PillarStatus;
  tone: Tone;
  score: number | null;
  scoreNote?: string;
  accent: string;
  info: { explainer: string; reading: string };
  footer?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function PillarCard(props: PillarCardProps) {
  const { name, measures, legend, status, tone, score, scoreNote, accent, info, footer, children, className } = props;
  const [open, setOpen] = useState(false);

  return (
    <Card className={cn("relative bg-card ring-white/8", className)} style={{ "--accent": accent } as CSSProperties}>
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-6 top-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }}
      />
      <CardHeader className="gap-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <span className="size-2 shrink-0 rounded-full" style={{ background: accent, boxShadow: `0 0 8px ${accent}` }} />
            <h2 className="font-heading truncate text-lg font-semibold tracking-tight">{name}</h2>
          </div>
          <StatusBadge status={status} />
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground text-pretty">{measures}</p>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="inline-flex w-fit items-center gap-1 rounded-md text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <Info className="size-3" />
          Was steckt dahinter?
          <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
        </button>

        {open ? (
          <div className="rounded-lg border border-border/60 bg-white/[0.02] p-3 text-xs leading-relaxed text-muted-foreground">
            <p className="text-pretty">{info.explainer}</p>
            <p className="mt-2 text-pretty text-foreground/80">{info.reading}</p>
            <p className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground/70">Denkschule: {legend}</p>
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4">
        <ScoreBar score={score} tone={tone} accent={accent} note={scoreNote} />
        {children}
      </CardContent>

      {footer ? (
        <CardFooter className="bg-transparent px-(--card-spacing) py-2.5 text-[11px] text-muted-foreground">{footer}</CardFooter>
      ) : null}
    </Card>
  );
}

function StatusBadge({ status }: { status: PillarStatus }) {
  if (status === "live") {
    return (
      <Badge variant="outline" className="gap-1.5 border-emerald-400/30 text-emerald-300">
        <span className="relative flex size-1.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-60" />
          <span className="relative inline-flex size-1.5 rounded-full bg-emerald-400" />
        </span>
        Live
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-muted-foreground">
      Demo-Daten
    </Badge>
  );
}

const TONE_CLASS: Record<Tone, string> = {
  bearish: "text-rose-300",
  neutral: "text-muted-foreground",
  bullish: "text-emerald-300",
};

function ScoreBar({ score, tone, accent, note }: { score: number | null; tone: Tone; accent: string; note?: string }) {
  const has = score != null;
  const s = has ? clampScore(score) : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Score</span>
        <span className="flex items-baseline gap-2">
          {has ? <span className={cn("text-[11px] font-medium", TONE_CLASS[tone])}>{TONE_LABEL[tone]}</span> : null}
          <span className="font-mono text-sm tabular-nums">
            {has ? s : "—"}
            <span className="text-muted-foreground">/100</span>
          </span>
        </span>
      </div>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-white/6">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${s}%`, background: accent, boxShadow: has ? `0 0 10px ${accent}` : undefined }}
        />
        <span aria-hidden className="absolute inset-y-0 left-1/2 w-px bg-white/15" />
      </div>
      {note ? <div className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground text-pretty">{note}</div> : null}
    </div>
  );
}

/** Kennzahl-Block: Label, grosser Wert, optionales Delta, Fussnote. */
export function MetricBlock({
  label,
  value,
  delta,
  note,
}: {
  label: string;
  value: ReactNode;
  delta?: { text: string; tone: Tone };
  note?: ReactNode;
}) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-heading text-3xl font-semibold tracking-tight tabular-nums">{value}</span>
        {delta ? (
          <span
            className={cn(
              "rounded-md px-1.5 py-0.5 font-mono text-xs tabular-nums",
              delta.tone === "bullish" && "bg-emerald-400/10 text-emerald-300",
              delta.tone === "bearish" && "bg-rose-400/10 text-rose-300",
              delta.tone === "neutral" && "bg-white/5 text-muted-foreground",
            )}
          >
            {delta.text}
          </span>
        ) : null}
      </div>
      {note ? <div className="mt-1 min-h-4 text-xs text-muted-foreground">{note}</div> : null}
    </div>
  );
}
