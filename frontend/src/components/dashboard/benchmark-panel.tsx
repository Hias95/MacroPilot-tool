"use client";

import { useEffect, useState } from "react";
import { ChartNoAxesColumn } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestPerformance, BacktestResponse, BacktestVariant, ZoneKey } from "@/lib/api";
import { THIN_EVIDENCE_EPISODES, liveVariant, loadBacktest } from "@/lib/backtest";
import { formatDateDe } from "@/lib/format";
import { ZONES } from "@/lib/score";
import { cn } from "@/lib/utils";

const pct = (n: number, digits = 1) => `${n > 0 ? "+" : ""}${n.toFixed(digits)} %`;

/** Der Backtest rechnet mit Kursen des ETF, gemeint ist der Index dahinter. */
const BENCHMARK_NAMES: Record<string, string> = { SPY: "S&P 500", QQQ: "Nasdaq 100", GLD: "Gold", IBIT: "Bitcoin" };
const benchmarkName = (ticker?: string) => (ticker ? (BENCHMARK_NAMES[ticker] ?? ticker) : "S&P 500");

const STRATEGIES: { key: keyof Pick<BacktestVariant, "buy_hold" | "strategy_base" | "strategy">; label: string; hint: string }[] = [
  { key: "buy_hold", label: "Immer voll investiert", hint: "Der Index ohne jede Regel, zum Vergleich." },
  { key: "strategy_base", label: "Zonen mit Grundquote", hint: "Quote zwischen 50 und 100 Prozent, nie ganz draußen." },
  { key: "strategy", label: "Zonen defensiv", hint: "Quote zwischen 0 und 100 Prozent, bei Stark negativ ganz draußen." },
];

const COLUMNS: { label: string; get: (p: BacktestPerformance) => string; hint: string }[] = [
  { label: "Rendite p. a.", get: (p) => pct(p.cagr_pct), hint: "Durchschnittlicher Wertzuwachs pro Jahr über den ganzen Zeitraum." },
  { label: "Schwankung", get: (p) => `${p.vol_pct.toFixed(1)} %`, hint: "Wie stark der Wert um seinen Trend schwankt, pro Jahr." },
  { label: "Größter Rückgang", get: (p) => `${p.max_drawdown_pct.toFixed(1)} %`, hint: "Der tiefste Absturz vom Höchststand bis zum Tiefpunkt." },
  { label: "Zeit im Markt", get: (p) => `${Math.round(p.avg_exposure * 100)} %`, hint: "Wie viel des Geldes im Schnitt investiert war." },
];

/**
 * B2, letzter offener Punkt: der Vergleich mit dem S&P 500. Zeigt zwei Dinge aus dem Backtest (C1):
 * was nach jeder Ampelzone historisch passiert ist, und wie sich eine Regel entlang der Zonen gegen
 * schlichtes Halten geschlagen haette. Historie, keine Prognose und keine Empfehlung.
 */
export function BenchmarkPanel({ currentZone }: { currentZone?: ZoneKey }) {
  const [data, setData] = useState<BacktestResponse | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    loadBacktest()
      .then((res) => alive && setData(res))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, []);

  if (data === null) return null;
  const variant = data ? liveVariant(data) : null;

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-4 py-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <ChartNoAxesColumn className="size-3.5" />
            Vergleich mit dem {benchmarkName(data?.benchmark)}
          </h2>
          {variant ? (
            <span className="text-[11px] text-muted-foreground/80">
              {formatDateDe(variant.start)} bis {formatDateDe(variant.end)} · {variant.weeks} Wochen
              {data?.benchmark ? ` · Kurse des ETF ${data.benchmark}` : ""}
            </span>
          ) : null}
        </div>

        {data === undefined ? <p className="text-xs text-muted-foreground">Lade Vergleich ...</p> : null}

        {variant ? (
          <>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground text-pretty">
              Rückblick, keine Prognose: So hat sich der Index nach Wochen in der jeweiligen Ampelzone entwickelt. Jede Woche kannte
              dabei nur ihre eigene Vergangenheit. Daneben steht, aus wie vielen getrennten Phasen eine Zone stammt. Weniger als
              zehn heißt: Die Zahlen beruhen auf einer Handvoll Fälle und können Zufall sein.
            </p>
            <ZoneTable variant={variant} currentZone={currentZone} />
            <StrategyTable variant={variant} />
            <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
              Grenzen des Rückblicks: Kosten, Steuern und Spreads sind nicht enthalten, Datenrevisionen bei Inflation und Umfragen
              lassen sich nicht rekonstruieren, und der Zeitraum umfasst nur einen einzigen langen Aufwärtsmarkt. Das Tool leitet
              daraus bewusst keine Quoten ab und gibt keine Anlageempfehlung.
            </p>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** Was folgte auf jede Zone? Balken = mittlere Indexrendite der folgenden 13 Wochen. */
function ZoneTable({ variant, currentZone }: { variant: BacktestVariant; currentZone?: ZoneKey }) {
  const max = Math.max(...variant.bands.map((b) => Math.abs(b.mean_fwd_13w)), 1);
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full min-w-[36rem] border-collapse text-sm">
        <caption className="sr-only">Mittlere Entwicklung des Vergleichsindex nach Wochen in der jeweiligen Ampelzone</caption>
        <thead>
          <tr className="text-[11px] uppercase tracking-wider text-muted-foreground">
            <th scope="col" className="py-1.5 text-left font-medium">Ampelzone</th>
            <th scope="col" className="py-1.5 text-right font-medium">Anteil, getrennte Phasen</th>
            <th scope="col" className="py-1.5 pl-5 text-left font-medium">Danach 13 Wochen</th>
            <th scope="col" className="py-1.5 text-right font-medium">davon positiv</th>
            <th scope="col" className="py-1.5 text-right font-medium">Danach 52 Wochen</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/60">
          {variant.bands.map((b) => {
            const zone = ZONES[b.key];
            const active = b.key === currentZone;
            return (
              <tr key={b.key} className={cn(active && "bg-white/5")}>
                <th scope="row" className="py-2 text-left font-normal">
                  <span className="flex items-center gap-2">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: zone?.color }} aria-hidden />
                    <span className={cn("truncate", active && "font-medium")}>{b.label}</span>
                    {active ? <span className="rounded border border-white/15 px-1 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">jetzt</span> : null}
                  </span>
                </th>
                <td className="py-2 text-right tabular-nums text-muted-foreground">
                  {b.share_pct.toFixed(0)} %
                  {/* Wochen ueberlappen sich. Getrennte Phasen sind das ehrlichere Mass und zeigen sofort,
                      dass die seltenen Zonen auf einer Handvoll Faelle beruhen. */}
                  <span className={cn("ml-1 text-[11px]", b.episodes > 0 && b.episodes < THIN_EVIDENCE_EPISODES ? "text-amber-300/90" : "text-muted-foreground/70")}>
                    {b.episodes} {b.episodes === 1 ? "Phase" : "Phasen"}
                  </span>
                </td>
                <td className="py-2 pl-5">
                  <span className="flex items-center gap-2">
                    <span className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full bg-white/8" aria-hidden>
                      <span className="block h-full rounded-full" style={{ width: `${Math.min(100, (Math.abs(b.mean_fwd_13w) / max) * 100)}%`, background: zone?.color }} />
                    </span>
                    <span className="tabular-nums">{pct(b.mean_fwd_13w)}</span>
                  </span>
                </td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">{b.hit_rate_13w.toFixed(0)} %</td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">{pct(b.mean_fwd_52w)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Regel entlang der Zonen gegen schlichtes Halten. Beide Regelvarianten sind Rechenbeispiele, keine Quoten-Empfehlung. */
function StrategyTable({ variant }: { variant: BacktestVariant }) {
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Hätte man den Zonen gefolgt statt einfach zu halten
      </h3>
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="w-full min-w-[36rem] border-collapse text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="py-1.5 text-left font-medium">Vorgehen</th>
              {COLUMNS.map((c) => (
                <th key={c.label} scope="col" className="py-1.5 pl-4 text-right font-medium" title={c.hint}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {STRATEGIES.map((s) => {
              const perf = variant[s.key];
              return (
                <tr key={s.key} className={cn(s.key === "buy_hold" && "text-muted-foreground")}>
                  <th scope="row" className="py-2 text-left font-normal">
                    <span className="block truncate font-medium text-foreground">{s.label}</span>
                    <span className="block text-[11px] text-muted-foreground/80">{s.hint}</span>
                  </th>
                  {COLUMNS.map((c) => (
                    <td key={c.label} className="py-2 pl-4 text-right tabular-nums">
                      {c.get(perf)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
        Lesart: Die Regeln kosteten Rendite und sparten Schwankung. Wer defensiv aussteigt, verpasst auch die Erholung, weil die
        stärksten Wochen oft direkt auf die schlechtesten folgen. Das Tool zeigt deshalb Zonen und Kräfte, nicht Prozentquoten.
      </p>
    </div>
  );
}
