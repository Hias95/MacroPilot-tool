"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ConsensusResponse, HistoryResponse, PillarResponse } from "@/lib/api";
import { availableRanges, filterByRange, useRange } from "@/lib/range";
import { MARKET_CONFIRM, PHASES, ZONES } from "@/lib/score";
import { ConsensusGauge } from "../consensus-gauge";
import { ConsensusHistoryChart } from "../consensus-history-chart";
import { RangeSelect } from "../range-select";
import { EasyPillarCard } from "./easy-pillar-card";

interface Props {
  consensus: ConsensusResponse;
  pillars: PillarResponse[];
  overlays: PillarResponse[];
  /** undefined = laedt noch, null = nicht verfuegbar */
  history: HistoryResponse | null | undefined;
}

/** Easy-Modus: Gesamtrang mit Ampelzone und Phase, dazu je Baustein Score, Ampel, Trend, Verlauf und ein Satz. */
export function EasyDashboard({ consensus, pillars, overlays, history }: Props) {
  const zone = ZONES[consensus.zone_key];
  const zoneRaw = ZONES[consensus.zone_raw_key];
  const unconfirmed = consensus.zone_raw_key !== consensus.zone_key;
  const phase = consensus.phase_key ? PHASES[consensus.phase_key] : null;
  const confirm = consensus.market_confirmation_key ? MARKET_CONFIRM[consensus.market_confirmation_key] : null;
  const regimes = [...pillars, ...overlays].map((p) => p.regime).filter((r): r is NonNullable<typeof r> => !!r && r.active);
  const [range, setRange] = useRange("consensus-easy", "1y");
  const [pillarRange, setPillarRange] = useRange("pillars-easy", "6m");
  const consensusPoints = history ? filterByRange(history.consensus, range) : [];
  const pointsOf = (id: string) => history?.pillars[id] ?? [];
  const longest = history ? Object.values(history.pillars).reduce<{ date: string }[]>((a, b) => (b.length > a.length ? b : a), history.consensus) : [];

  return (
    <>
      <Card className="bg-card ring-white/8">
        <CardContent className="grid gap-6 py-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] lg:items-center lg:gap-10">
          <div>
            <div className="mb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Gesamtlage</div>
            <ConsensusGauge score={consensus.score ?? 50} zone={{ label: zone.label, color: zone.color }} />
          </div>
          <div className="flex flex-col gap-4">
            <div>
              <div className="font-heading text-3xl font-semibold tracking-tight" style={{ color: zone.color }}>
                {consensus.zone}
              </div>
              <p className="mt-1 text-sm text-foreground/90">
                Besser als <span className="font-mono tabular-nums">{consensus.score ?? "—"} %</span> der Wochen der letzten zehn Jahre
                {consensus.weeks_in_zone ? `, seit ${consensus.weeks_in_zone} Wochen in dieser Zone` : ""}.
              </p>
              <p className="mt-1.5 max-w-lg text-sm leading-relaxed text-muted-foreground text-pretty">{zone.hint}</p>
              {unconfirmed ? (
                <p className="mt-1.5 text-xs text-amber-300/90 text-pretty">
                  Diese Woche zeigt bereits <span style={{ color: zoneRaw.color }}>{zoneRaw.label}</span>, die Zone wechselt erst nach drei Wochen in Folge.
                </p>
              ) : null}
              {phase ? (
                <p className="mt-2 text-sm text-muted-foreground text-pretty">
                  Zyklusphase: <span className="font-medium text-foreground">{phase.label}</span>
                  {consensus.weeks_in_phase ? `, seit ${consensus.weeks_in_phase} Wochen` : ""}. {phase.hint}
                </p>
              ) : null}
              {confirm ? (
                <p className="mt-2 text-sm text-muted-foreground text-pretty">
                  <span className={confirm.tone === "good" ? "font-medium text-emerald-300" : confirm.tone === "warn" ? "font-medium text-amber-300" : "font-medium text-rose-300"}>
                    {confirm.label}:
                  </span>{" "}
                  {confirm.hint}
                </p>
              ) : null}
              {regimes.length > 0 ? (
                <ul className="mt-2 space-y-1 text-sm text-amber-300/90">
                  {regimes.map((r) => (
                    <li key={r.id} className="text-pretty">
                      <span className="font-medium">{r.label} aktiv:</span> <span className="text-foreground/80">{r.hint}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
            <div>
              <div className="mb-1 flex flex-wrap items-center justify-between gap-2 text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
                <span>Verlauf</span>
                {history ? <RangeSelect value={range} onChange={setRange} available={availableRanges(history.consensus)} /> : null}
              </div>
              {history === undefined ? <Skeleton className="h-[150px] w-full" /> : null}
              {history === null ? <p className="text-xs text-muted-foreground">Verlauf nicht verfügbar.</p> : null}
              {consensusPoints.length > 0 ? <ConsensusHistoryChart data={consensusPoints} height={150} /> : null}
            </div>
          </div>
        </CardContent>
      </Card>

      <section aria-label="Die drei Treiber" className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Die drei Treiber</h2>
          <span className="flex items-center gap-2 text-[11px] text-muted-foreground">
            Verlauf
            {history ? <RangeSelect value={pillarRange} onChange={setPillarRange} available={availableRanges(longest)} /> : null}
          </span>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {pillars.map((p) => (
            <EasyPillarCard key={p.id} pillar={p} points={pointsOf(p.id)} range={pillarRange} />
          ))}
        </div>
      </section>

      {overlays.length > 0 ? (
        <section aria-label="Bremsen und Verstärker" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-baseline gap-3">
            <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Bremsen und Verstärker</h2>
            <span className="text-[11px] text-muted-foreground/70">Bewertung zeigt die Fallhöhe, Markttechnik die kurzfristige Kaskadengefahr, Marktsignale, ob der Markt das Bild bestätigt.</span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {overlays.map((p) => (
              <EasyPillarCard key={p.id} pillar={p} points={pointsOf(p.id)} range={pillarRange} compact />
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
