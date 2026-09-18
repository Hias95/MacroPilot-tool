"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchDashboard, fetchHistory, type DashboardResponse, type HistoryResponse } from "@/lib/api";
import { useViewMode } from "@/lib/mode";
import { ZONES, isValuationExtreme, marketConfirmedOf } from "@/lib/score";
import { BenchmarkPanel } from "./benchmark-panel";
import { ChangesPanel } from "./changes-panel";
import { LimitsPanel } from "./limits-panel";
import { OutlookPanel } from "./outlook-panel";
import { EasyDashboard } from "./easy/easy-dashboard";
import { ConsensusPanel } from "./consensus-panel";
import { PillarTile } from "./pillar-tile";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: DashboardResponse };

/** Laedt alle Saeulen plus Consensus in einem Request und rendert das Dashboard. */
export function DashboardClient() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [history, setHistory] = useState<HistoryResponse | null | undefined>(undefined);
  const mode = useViewMode();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchDashboard(controller.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
      });
    fetchHistory(20, controller.signal)
      .then((h) => setHistory(h))
      .catch(() => {
        if (!controller.signal.aborted) setHistory(null);
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = () => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  if (state.status === "loading") {
    return (
      <>
        <Card className="bg-card ring-white/8">
          <CardContent className="grid gap-8 py-3 lg:grid-cols-2">
            <Skeleton className="mx-auto h-56 w-full max-w-md rounded-2xl" />
            <div className="space-y-3">
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-8 w-32" />
              <Skeleton className="h-3 w-72" />
              <Skeleton className="h-3 w-64" />
            </div>
          </CardContent>
        </Card>
        <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Card key={i} className="bg-card ring-white/8">
              <CardContent className="space-y-3 py-2">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-1.5 w-full" />
                <Skeleton className="h-9 w-40" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </section>
      </>
    );
  }

  if (state.status === "error") {
    return (
      <Card className="border-rose-400/20 bg-rose-400/5 ring-0">
        <CardContent className="flex flex-col items-start gap-3 py-2 text-sm">
          <div className="font-medium text-rose-200">Backend antwortet nicht</div>
          <p className="text-muted-foreground text-pretty">{state.message}</p>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={retry}>
            <RefreshCw className="size-3.5" />
            Erneut versuchen
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { consensus, pillars, overlays } = state.data;
  if (mode === "easy") {
    return (
      <>
        <EasyDashboard consensus={consensus} pillars={pillars} overlays={overlays} history={history} />
        <ChangesPanel days={90} compact />
      </>
    );
  }
  return (
    <>
      <ConsensusPanel consensus={consensus} pillars={pillars} overlays={overlays} history={history ? history.consensus : history} />
      <OutlookPanel
        zoneKey={consensus.zone_key}
        zoneLabel={consensus.zone}
        zoneColor={ZONES[consensus.zone_key].color}
        valuationExtreme={isValuationExtreme(overlays)}
        marketConfirmed={marketConfirmedOf(consensus)}
      />
      <ChangesPanel days={365} />
      <section aria-label="Die drei Treiber" className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {pillars.map((p) => (
          <PillarTile key={p.id} pillar={p} />
        ))}
      </section>
      {overlays.length > 0 ? (
        <section aria-label="Overlays" className="flex flex-col gap-3">
          <div className="flex items-baseline gap-3">
            <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Overlays: Verstärker und Bremsen</h2>
            <span className="text-[11px] text-muted-foreground/70">Keine Treiber des Consensus, sondern Deckel, Kontra-Korrektur und Bestätigung.</span>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {overlays.map((p) => (
              <PillarTile key={p.id} pillar={p} />
            ))}
          </div>
        </section>
      ) : null}
      <BenchmarkPanel currentZone={consensus.zone_key} />
      <LimitsPanel />
    </>
  );
}
