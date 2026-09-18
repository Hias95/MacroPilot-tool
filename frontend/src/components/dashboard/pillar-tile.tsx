"use client";

import { useState } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Component, Frequency, PillarResponse, Point, RegimeFlag } from "@/lib/api";
import { ageText, formatChange, formatPeriod, formatSignedPct, formatSpan, formatValue } from "@/lib/format";
import { PILLAR_UI } from "@/lib/pillars";
import { availableRanges, filterByRange, useRange } from "@/lib/range";
import { toneForChange } from "@/lib/score";
import { cn } from "@/lib/utils";
import { Explanation } from "./explanation";
import { MetricBlock, PillarCard } from "./pillar-card";
import { RangeSelect } from "./range-select";
import { Sparkline } from "./sparkline";

const SOURCE_LABELS: Array<[string, string]> = [
  ["yahoo", "Yahoo Finance"],
  ["fred-api", "FRED (API)"],
  ["fred", "FRED"],
  ["shillerdata", "Shiller (shillerdata.com)"],
  ["yale", "Shiller (Yale, veraltet)"],
  ["cboe", "CBOE"],
  ["treasury", "US Treasury"],
];

function sourceLabel(source: string): string {
  return SOURCE_LABELS.find(([prefix]) => source.startsWith(prefix))?.[1] ?? source;
}

/** Eine Saeule: Kopf, Score, Hauptkennzahl (folgt dem Cursor im Chart), Bestandteile, KI-Erklaerung. */
export function PillarTile({ pillar }: { pillar: PillarResponse }) {
  const ui = PILLAR_UI[pillar.id];
  const [hover, setHover] = useState<Point | null>(null);
  const [range, setRange] = useRange(`tile-${pillar.id}`, "1y");
  const shown = filterByRange(pillar.history, range);
  const fmt = pillar.headline.format;
  const change = pillar.change_13w;

  const freq = pillar.frequency;
  const value = hover ? hover.value : pillar.headline.value;
  const pctBased = fmt === "usd_millions" || fmt === "ratio" || fmt === "price";
  const longChange = (c: typeof pillar.change_52w) =>
    c ? `${formatSpan(c.weeks, freq)} ${pctBased ? formatSignedPct(c.pct) : formatChange(c, fmt, freq).split(" / ")[0]}` : null;
  const note = hover ? (
    <span className="font-mono tabular-nums">{freq === "monthly" ? formatPeriod(hover.date, freq) : `am ${formatPeriod(hover.date, freq)}`}</span>
  ) : (
    <span className="font-mono tabular-nums">
      {[longChange(pillar.change_1w), longChange(pillar.change_52w)].filter(Boolean).join(" · ")}
    </span>
  );

  return (
    <PillarCard
      name={pillar.name}
      measures={pillar.measures}
      legend={pillar.legend}
      status={pillar.status}
      tone={pillar.tone}
      score={pillar.score?.score ?? null}
      scoreNote={pillar.score_note}
      accent={ui.accent}
      info={{ explainer: ui.explainer, reading: ui.reading }}
      footer={
        <span>
          {/* Nicht nur wann, sondern wie alt: Die Saeulen melden in sehr unterschiedlichem Takt, und der
              Gesamtscore mischt sie, ohne dass man das sonst saehe. */}
          Stand {formatPeriod(pillar.headline.date, freq)}, {ageText(pillar.headline.date)} &middot; Quelle{" "}
          {sourceLabel(pillar.source)}
        </span>
      }
    >
      {/* Was die Kachel fuer den Gesamtscore tut. Ohne diesen Satz bleibt unklar, warum sie da ist. */}
      {pillar.easy_role ? (
        <p className="text-[11px] leading-relaxed text-muted-foreground/70 text-pretty">{pillar.easy_role}</p>
      ) : null}
      <MetricBlock
        label={pillar.headline.label}
        value={formatValue(value, fmt)}
        delta={change && !hover ? { text: formatChange(change, fmt, freq), tone: toneForChange((pctBased ? change.pct : change.abs) * (pillar.headline.sign === "-" ? -1 : 1)) } : undefined}
        note={note}
      />

      {pillar.history.length > 1 ? (
        <div className="flex flex-col gap-1">
          <div className="flex justify-end">
            <RangeSelect value={range} onChange={setRange} available={availableRanges(pillar.history)} />
          </div>
          <Sparkline data={shown} color={ui.accent} id={pillar.id} onHover={setHover} />
        </div>
      ) : null}

      {pillar.components.length > 0 ? <ComponentList components={pillar.components} frequency={freq} /> : null}

      {pillar.regime ? <RegimeBlock regime={pillar.regime} /> : null}

      <Explanation pillarId={pillar.id} fingerprint={pillar.fingerprint} accent={ui.accent} />
    </PillarCard>
  );
}

function ComponentList({ components, frequency }: { components: Component[]; frequency: Frequency }) {
  return (
    <div className="flex flex-col gap-1.5 text-xs">
      {components.map((c) => {
        // Farbe zeigt die Wirkung auf die Hauptkennzahl: ein steigender Minus-Posten ist schlecht.
        const usesPoints = c.format === "index" || c.format === "diffusion" || c.format === "percent" || c.format === "pp";
        const raw = usesPoints ? c.change_13w_abs : c.change_13w_pct;
        const effect = raw == null ? null : c.sign === "-" ? -raw : raw;
        const tone = toneForChange(effect);
        const changeText = raw == null ? null : usesPoints ? `${raw > 0 ? "+" : raw < 0 ? "−" : ""}${Math.abs(raw).toLocaleString("de-DE", { maximumFractionDigits: c.format === "percent" || c.format === "pp" ? 2 : 1 })} ${c.format === "percent" || c.format === "pp" ? "Pp." : "Pkt."}` : formatSignedPct(raw, 1);
        return (
          <div key={c.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-x-2.5">
            <Tooltip>
              <TooltipTrigger className="flex min-w-0 items-start gap-1.5 text-left leading-snug break-words text-muted-foreground underline decoration-dotted decoration-muted-foreground/40 underline-offset-2 hover:text-foreground">
                <span className="w-2.5 shrink-0 text-center font-mono text-muted-foreground/60">{c.sign === "-" ? "−" : "+"}</span>
                <span>{c.label}</span>
                {c.score != null ? (
                  <span className="ml-1 shrink-0 rounded bg-white/6 px-1 font-mono text-[10px] tabular-nums text-foreground/80" title="Teil-Score 0 bis 100">
                    {c.score}
                  </span>
                ) : null}
              </TooltipTrigger>
              {c.note ? (
                <TooltipContent side="top" className="max-w-64 text-pretty">
                  {c.note}
                </TooltipContent>
              ) : null}
            </Tooltip>
            <span className="whitespace-nowrap text-right font-mono tabular-nums">{formatValue(c.value, c.format)}</span>
            <span
              title={`Veränderung über ${formatSpan(13, frequency)}`}
              className={cn(
                "min-w-14 whitespace-nowrap text-right font-mono text-[11px] tabular-nums",
                tone === "bullish" && "text-emerald-300/80",
                tone === "bearish" && "text-rose-300/80",
                tone === "neutral" && "text-muted-foreground/70",
              )}
            >
              {changeText ?? ""}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function RegimeBlock({ regime }: { regime: RegimeFlag }) {
  return (
    <div className={cn("rounded-lg border p-3 text-xs", regime.active ? "border-amber-400/30 bg-amber-400/5" : "border-border/60 bg-white/[0.02]")}>
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-medium">
          Regime-Check: {regime.label}{" "}
          <span className={regime.active ? "text-amber-300" : "text-muted-foreground"}>{regime.active ? "aktiv" : "nicht aktiv"}</span>
        </span>
        {/* Zwei verschiedene Zahlen: wie viele der Kriterien erfuellt sind, und ab wie vielen das Regime gilt.
            Frueher stand hier "2 von 2", waehrend drei Kriterien darunter aufgelistet waren. */}
        <span className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
          {regime.met_count} von {regime.criteria.length} erfüllt, nötig {regime.needed}
        </span>
      </div>
      <ul className="space-y-1 text-muted-foreground">
        {regime.criteria.map((c) => (
          <li key={c.label} className="flex items-start gap-1.5">
            <span className={cn("w-3 shrink-0 text-center", c.met ? "text-amber-300" : "text-muted-foreground/50")}>{c.met ? "✓" : "–"}</span>
            <span className="min-w-0">
              {c.label}: <span className="font-mono tabular-nums text-foreground/80">{c.value_text}</span>
            </span>
          </li>
        ))}
      </ul>
      {regime.active ? <p className="mt-2 leading-relaxed text-foreground/80 text-pretty">{regime.hint}</p> : null}
    </div>
  );
}
