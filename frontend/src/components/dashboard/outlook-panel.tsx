"use client";

import { useEffect, useState } from "react";
import { Telescope } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestBand, ZoneKey } from "@/lib/api";
import { OUTLOOK_LABEL, THIN_EVIDENCE_EPISODES, bandFor, liveVariant, loadBacktest } from "@/lib/backtest";
import { cn } from "@/lib/utils";

// Genau zehn Punkte, damit der Streifen eins zu eins zum Satz "X von 10" passt. Eine feinere Aufloesung
// waere genauer, aber der Leser muesste zwischen zwei Zahlen umrechnen, und genau das soll er nicht.
const DOTS = 10;
const pct = (n: number, digits = 1) => `${n > 0 ? "+" : ""}${n.toFixed(digits)} %`;

interface Loaded {
  band: BacktestBand;
  benchmark: string;
  startYear: number;
}

/**
 * Der Erwartungssatz: uebersetzt den Rang in eine Aussage mit Bezugsklasse, Zeitraum und Spannweite.
 *
 * Form und Wortwahl folgen der Risikokommunikation: natuerliche Haeufigkeit statt Prozentsatz
 * ("8 von 10"), die Bezugsklasse ausdruecklich genannt ("Wochen wie diese"), der Zeitraum immer dabei,
 * und ein abzaehlbarer Streifen statt einer glatten Kurve. Alle Zahlen stammen aus abgezaehlter Historie,
 * nichts ist modelliert.
 */
export function OutlookPanel({ zoneKey, zoneLabel, zoneColor }: { zoneKey: ZoneKey; zoneLabel: string; zoneColor: string }) {
  const [data, setData] = useState<Loaded | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    loadBacktest()
      .then((res) => {
        const variant = liveVariant(res);
        const band = variant ? bandFor(variant, zoneKey) : null;
        if (!alive) return;
        setData(band && variant ? { band, benchmark: res.benchmark, startYear: new Date(variant.start).getFullYear() } : null);
      })
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, [zoneKey]);

  if (data === null) return null;

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Telescope className="size-3.5" />
          Was folgte auf Wochen wie diese?
        </h2>
        {data === undefined ? (
          <p className="text-xs text-muted-foreground">Lade Vergleichswochen ...</p>
        ) : (
          <Outlook {...data} zoneLabel={zoneLabel} zoneColor={zoneColor} />
        )}
      </CardContent>
    </Card>
  );
}

function Outlook({ band, benchmark, startYear, zoneLabel, zoneColor }: Loaded & { zoneLabel: string; zoneColor: string }) {
  const hit = band.hit_rate_13w;
  if (hit == null || !band.n_13w) {
    return <p className="text-sm text-muted-foreground text-pretty">Für diese Zone liegen noch zu wenige Vergleichswochen vor.</p>;
  }
  const outOfTen = Math.round(hit / 10);
  const green = outOfTen;
  const thin = band.episodes > 0 && band.episodes < THIN_EVIDENCE_EPISODES;
  const index = benchmark === "SPY" ? "S&P 500" : benchmark;

  return (
    <>
      <p className="max-w-3xl text-base leading-relaxed text-pretty">
        In <strong className="font-semibold tabular-nums">{outOfTen} von 10</strong> Wochen mit der Ampelzone{" "}
        <span className="font-medium" style={{ color: zoneColor }}>{zoneLabel}</span> stand der {index}{" "}
        <strong className="font-semibold">{OUTLOOK_LABEL} später</strong> höher.
      </p>

      <div className="flex flex-col gap-1.5">
        <div className="flex flex-wrap gap-1.5" role="img"
             aria-label={`${green} von ${DOTS} vergleichbaren Wochen endeten nach ${OUTLOOK_LABEL} im Plus`}>
          {Array.from({ length: DOTS }, (_, i) => (
            <span
              key={i}
              className={cn("size-4 rounded-full", i < green ? "bg-emerald-400/90" : "bg-rose-400/80")}
            />
          ))}
        </div>
        <p className="text-[11px] text-muted-foreground/80">
          Jeder Punkt steht für eine von zehn vergleichbaren Wochen. Grün: Der Index stand {OUTLOOK_LABEL} später höher.
          Tatsächlich waren es {hit.toFixed(0)} Prozent.
        </p>
      </div>

      {band.p50_fwd_13w != null ? (
        <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Typisch</dt>
            <dd className="tabular-nums">{pct(band.p50_fwd_13w)}</dd>
          </div>
          {band.p10_fwd_13w != null ? (
            <div>
              <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Schlechtestes Zehntel</dt>
              <dd className="tabular-nums">{pct(band.p10_fwd_13w)}</dd>
            </div>
          ) : null}
          {band.p90_fwd_13w != null ? (
            <div>
              <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">Bestes Zehntel</dt>
              <dd className="tabular-nums">{pct(band.p90_fwd_13w)}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      <p className={cn("max-w-3xl text-[11px] leading-relaxed text-pretty", thin ? "text-amber-300/90" : "text-muted-foreground/80")}>
        Grundlage: {band.n_13w} vergleichbare Wochen aus {band.episodes} getrennten Phasen seit {startYear}.
        {thin
          ? ` Das sind wenige unabhängige Phasen. Die Zahlen sind entsprechend unsicher und können auf Zufall beruhen.`
          : ""}{" "}
        Rückblick, keine Prognose: Die Zukunft muss sich nicht an die Vergangenheit halten.
      </p>
    </>
  );
}
