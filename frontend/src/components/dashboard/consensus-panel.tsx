import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ConsensusHistoryPoint, ConsensusResponse, PhaseKey, PillarResponse } from "@/lib/api";
import { PILLAR_UI } from "@/lib/pillars";
import { availableRanges, filterByRange, useRange } from "@/lib/range";
import { MARKET_CONFIRM, PHASES, ZONES } from "@/lib/score";
import { cn } from "@/lib/utils";
import { ConsensusGauge } from "./consensus-gauge";
import { ConsensusHistoryChart } from "./consensus-history-chart";
import { RangeSelect } from "./range-select";

interface Props {
  consensus: ConsensusResponse;
  pillars: PillarResponse[];
  overlays?: PillarResponse[];
  /** undefined = laedt noch, null = nicht verfuegbar */
  history?: ConsensusHistoryPoint[] | null;
}

const VETO_LABEL: Record<string, string> = {
  liquidity: "Liquiditätskrise",
  structure: "Strukturkrise",
  valuation_mechanics: "Bewertung + Markttechnik",
};
const PHASE_ORDER: PhaseKey[] = ["recovery", "expansion", "late", "downturn"];
const num = (n: number | null | undefined, digits = 0) =>
  n == null ? "—" : n.toLocaleString("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits });
const signed = (n: number, digits = 1) => `${n >= 0 ? "+" : "−"}${num(Math.abs(n), digits)}`;

export function ConsensusPanel({ consensus, pillars, overlays = [], history }: Props) {
  const zone = ZONES[consensus.zone_key];
  const zoneRaw = ZONES[consensus.zone_raw_key];
  const confirm = consensus.market_confirmation_key ? MARKET_CONFIRM[consensus.market_confirmation_key] : null;
  const [range, setRange] = useRange("consensus-pro", "max");
  const shown = history ? filterByRange(history, range) : history;
  const unconfirmed = consensus.zone_raw_key !== consensus.zone_key;
  const score = consensus.score ?? 50;
  const regimes = [...pillars, ...overlays].map((p) => p.regime).filter((r): r is NonNullable<typeof r> => !!r && r.active);
  const v2 = consensus.method.startsWith("macropilot-v2");
  const capBinds = consensus.cap != null && consensus.adjusted != null && consensus.adjusted > consensus.cap;

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="grid gap-8 py-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)] lg:items-center lg:gap-12">
        <div>
          <div className="mb-1 flex flex-wrap items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Consensus Score
            <Badge variant="outline" className="normal-case tracking-normal text-muted-foreground">
              {pillars.length} Treiber, {overlays.length} Overlays
            </Badge>
            {consensus.vetoes.map((v) => (
              <Badge key={v} variant="outline" className="border-rose-400/40 normal-case tracking-normal text-rose-300">
                Veto: {VETO_LABEL[v] ?? v}
              </Badge>
            ))}
            {regimes.map((r) => (
              <Badge key={r.id} variant="outline" className="border-amber-400/30 normal-case tracking-normal text-amber-300" title={r.hint}>
                {r.label} aktiv
              </Badge>
            ))}
          </div>
          <ConsensusGauge score={score} zone={{ label: zone.label, color: zone.color }} />
          {v2 ? (
            <div className="mx-auto mt-2 flex max-w-[440px] justify-center gap-6 text-xs text-muted-foreground">
              <Direction label="Liquidität" dir={consensus.liquidity_direction} />
              <Direction label="Konjunktur" dir={consensus.growth_direction} />
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-5">
          <div>
            <div className="flex items-baseline justify-between text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              <span>Zone</span>
              {consensus.weeks_in_zone ? <span className="normal-case tracking-normal">seit {consensus.weeks_in_zone} Wochen</span> : null}
            </div>
            <div className="mt-1 font-heading text-3xl font-semibold tracking-tight" style={{ color: zone.color }}>
              {consensus.zone}
            </div>
            <p className="mt-1 text-sm text-foreground/90">
              Besser als <span className="font-mono tabular-nums">{consensus.score ?? "—"} %</span> der Wochen der letzten zehn Jahre.
            </p>
            <p className="mt-2 max-w-md text-sm text-muted-foreground text-pretty">{zone.hint}</p>
            {unconfirmed ? (
              <p className="mt-2 text-xs text-amber-300/90 text-pretty">
                Diese Woche zeigt bereits <span style={{ color: zoneRaw.color }}>{zoneRaw.label}</span>. Die Zone wechselt erst nach drei Wochen in Folge.
              </p>
            ) : null}
            {confirm ? (
              <p className="mt-2 flex flex-wrap items-baseline gap-x-2 text-xs text-muted-foreground text-pretty">
                <Badge
                  variant="outline"
                  className={cn(
                    "normal-case tracking-normal",
                    confirm.tone === "good" && "border-emerald-400/40 text-emerald-300",
                    confirm.tone === "warn" && "border-amber-400/40 text-amber-300",
                    confirm.tone === "bad" && "border-rose-400/40 text-rose-300",
                  )}
                >
                  {confirm.label}
                </Badge>
                <span>{confirm.hint}</span>
              </p>
            ) : null}
          </div>

          {v2 && consensus.phase_key ? (
            <PhaseTrack phase={consensus.phase_key} raw={consensus.phase_raw_key} weeks={consensus.weeks_in_phase} knapp={consensus.confidence === "knapp"} />
          ) : null}

          <div className="rounded-lg border border-border/60 bg-white/[0.02] p-3">
            <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Warum diese Einordnung?</div>
            <p className="text-sm leading-relaxed text-foreground/90 text-pretty">{consensus.why}</p>
          </div>

          <div className="flex flex-col gap-2.5">
            <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">So stimmen die Treiber ab</div>
            {pillars.map((p) => (
              <ScoreRow key={p.id} label={p.name} score={consensus.pillar_scores[p.id] ?? null} accent={PILLAR_UI[p.id].accent} />
            ))}
            {overlays.length > 0 ? <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">Overlays</div> : null}
            {overlays.map((p) => (
              <ScoreRow
                key={p.id}
                label={
                  p.id === "valuation"
                    ? `${p.name} · Deckel ${num(consensus.valuation_cap)}`
                    : p.id === "mechanics"
                      ? `${p.name} · ${signed(consensus.mechanics_adjustment)}`
                      : `${p.name} · ${consensus.market_confirmation ?? "Bestätigung"}`
                }
                score={consensus.overlay_scores[p.id] ?? null}
                accent={PILLAR_UI[p.id].accent}
              />
            ))}
            {v2 && consensus.core != null ? (
              <p className="font-mono text-[11px] tabular-nums text-muted-foreground/80">
                Kern {num(consensus.core, 1)} &middot; Mechanik {signed(consensus.mechanics_adjustment)} &middot; Deckel {num(consensus.cap, 1)}
                {capBinds ? " (greift)" : ""} &rarr; Rohwert {num(consensus.composite)} &rarr; Rang {consensus.score}
              </p>
            ) : null}
            <p className="text-[11px] leading-relaxed text-muted-foreground/70 text-pretty">{consensus.note}</p>
          </div>
        </div>

        <div className="lg:col-span-2">
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
            <span>Consensus-Verlauf, wöchentlich, Rang gegenüber den zehn Jahren davor</span>
            <span className="flex items-center gap-2 normal-case tracking-normal">
              {shown && shown.length > 0 ? <span>seit {shown[0].date.slice(0, 7).replace("-", "/")}</span> : null}
              {history && history.length > 0 ? <RangeSelect value={range} onChange={setRange} available={availableRanges(history)} /> : null}
            </span>
          </div>
          {history === undefined ? <Skeleton className="h-[190px] w-full" /> : null}
          {history === null ? <p className="text-xs text-muted-foreground">Verlauf nicht verfügbar.</p> : null}
          {shown && shown.length > 0 ? <ConsensusHistoryChart data={shown} /> : null}
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreRow({ label, score, accent }: { label: string; score: number | null; accent: string }) {
  return (
    <div className="grid grid-cols-[minmax(120px,1.4fr)_minmax(0,1fr)_32px] items-center gap-3 text-xs">
      <span className="truncate text-muted-foreground">{label}</span>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/6">
        <div className="h-full rounded-full" style={{ width: `${score ?? 0}%`, background: accent }} />
      </div>
      <span className="text-right font-mono tabular-nums">{score ?? "—"}</span>
    </div>
  );
}

function PhaseTrack({ phase, raw, weeks, knapp }: { phase: PhaseKey; raw: PhaseKey | null; weeks: number | null; knapp: boolean }) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
        <span>Zyklusphase</span>
        <span className="normal-case tracking-normal">
          {PHASES[phase].label}
          {weeks ? ` · seit ${weeks} Wochen` : ""}
          {knapp ? " · knapp" : ""}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-1">
        {PHASE_ORDER.map((key) => {
          const active = key === phase;
          const pending = !active && key === raw;
          return (
            <div
              key={key}
              title={PHASES[key].hint}
              className={cn(
                "rounded-md border px-2 py-1.5 text-center text-[11px] transition-colors",
                active ? "border-foreground/40 bg-white/10 font-medium text-foreground" : "border-border/60 text-muted-foreground",
                pending && "border-dashed border-amber-400/50 text-amber-300",
              )}
            >
              {PHASES[key].label}
              {pending ? <span className="block text-[9px] uppercase tracking-wider">Rohsignal</span> : null}
            </div>
          );
        })}
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground/80 text-pretty">{PHASES[phase].hint}</p>
    </div>
  );
}

function Direction({ label, dir }: { label: string; dir: "up" | "down" | null }) {
  if (!dir) return null;
  const up = dir === "up";
  return (
    <span className={cn("inline-flex items-center gap-1", up ? "text-emerald-300/90" : "text-rose-300/90")}>
      {up ? <ArrowUpRight className="size-3.5" /> : <ArrowDownRight className="size-3.5" />}
      {label} {up ? "steigt" : "fällt"}
    </span>
  );
}
