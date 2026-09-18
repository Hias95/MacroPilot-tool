"use client";

import { useEffect, useState } from "react";
import { ChartNoAxesColumn } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestPerformance, BacktestResponse, BacktestVariant, BenchmarkResult, ZoneKey } from "@/lib/api";
import { THIN_EVIDENCE_EPISODES, liveVariant, loadBacktest, zoneBandOf } from "@/lib/backtest";
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
            {data?.early_window && data?.test_window ? (
              <EraNote early={data.early_window} late={data.test_window} />
            ) : null}
            {data?.benchmarks?.length && currentZone ? (
              <OtherAssets benchmarks={data.benchmarks} zone={currentZone} zoneLabel={zoneLabelOf(variant, currentZone)} />
            ) : null}
            <StrategyTable variant={variant} />
            <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
              Grenzen des Rückblicks: Kosten, Steuern und Spreads sind nicht enthalten, und der Zeitraum umfasst nur einen einzigen
              langen Aufwärtsmarkt. Dazu kommt ein Punkt, der die Zahlen zu freundlich macht: Inflation, Umfragen und
              Schuldendienst werden nachträglich revidiert. Der Rückblick rechnet mit den heute gültigen Werten, die es damals so
              noch nicht gab. Die eingebauten Veröffentlichungsverzögerungen verschieben nur den Zeitpunkt, nicht den Wert. Das
              Tool leitet daraus bewusst keine Quoten ab und gibt keine Anlageempfehlung.
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
  // "Praktisch nichts gespart" heisst: weniger als einen Prozentpunkt besser als schlichtes Halten.
  const baseSavedNothing = variant.strategy_base.max_drawdown_pct - variant.buy_hold.max_drawdown_pct < 1;
  const fmtPct = (n: number) => `${n.toFixed(1)} %`;
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
      {/* C5: Das wichtigste Negativergebnis stand bisher nicht da. Die Regel mit Grundquote senkt die
          Schwankung, aber beim groessten Rueckgang half sie im Rueckblick praktisch nicht. */}
      <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
        Lesart: Die Regeln kosteten Rendite und sparten Schwankung.{" "}
        {baseSavedNothing ? (
          <span className="text-amber-300/90">
            Beim größten Rückgang half die Grundquoten-Regel dabei praktisch nicht ({fmtPct(variant.strategy_base.max_drawdown_pct)}{" "}
            gegen {fmtPct(variant.buy_hold.max_drawdown_pct)}), sie kostete nur Rendite. Ein ruhigerer Verlauf ist nicht dasselbe wie
            weniger Absturz.
          </span>
        ) : (
          `Beim größten Rückgang brachte die Grundquoten-Regel ${fmtPct(variant.strategy_base.max_drawdown_pct)} statt ${fmtPct(variant.buy_hold.max_drawdown_pct)}.`
        )}{" "}
        Wer defensiv aussteigt, verpasst auch die Erholung, weil die stärksten Wochen oft direkt auf die schlechtesten folgen. Das
        Tool zeigt deshalb Zonen und Kräfte, nicht Prozentquoten.
      </p>
    </div>
  );
}

/** Das Label der aktuellen Zone aus der Bänder-Tabelle, damit die Überschrift die Zone benennt. */
function zoneLabelOf(variant: BacktestVariant, zone: ZoneKey): string {
  return variant.bands.find((b) => b.key === zone)?.label ?? "dieser Zone";
}

/**
 * C1: Sagt der Consensus auch etwas über Gold, Anleihen und eine Mischung?
 *
 * Das Regime-Flag "Fiskalische Dominanz" behauptet, Sachwerte und Gold profitierten historisch. Bisher stand
 * diese Behauptung ohne eine einzige Zahl da, in einem Werkzeug, das sonst alles belegt. Gezeigt wird nur die
 * aktuelle Zone, sonst wäre es eine Tabelle mit fünfundzwanzig Feldern.
 */
function OtherAssets({ benchmarks, zone, zoneLabel }: { benchmarks: BenchmarkResult[]; zone: ZoneKey; zoneLabel: string }) {
  const rows = benchmarks
    .map((b) => ({ name: b.name, band: zoneBandOf(b, zone) }))
    .filter((r): r is { name: string; band: NonNullable<ReturnType<typeof zoneBandOf>> } => r.band?.hit_rate_13w != null);
  if (rows.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Und die anderen Anlagen? Nach Wochen in der Zone {zoneLabel}
      </h3>
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="w-full min-w-[30rem] border-collapse text-sm">
          <thead>
            <tr className="text-[11px] uppercase tracking-wider text-muted-foreground">
              <th scope="col" className="py-1.5 text-left font-medium">Anlage</th>
              <th scope="col" className="py-1.5 pl-4 text-right font-medium">Nach 13 Wochen im Plus</th>
              <th scope="col" className="py-1.5 pl-4 text-right font-medium">Typisch</th>
              <th scope="col" className="py-1.5 pl-4 text-right font-medium">Phasen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {rows.map((r) => (
              <tr key={r.name}>
                <th scope="row" className="py-2 text-left font-normal">{r.name}</th>
                <td className="py-2 pl-4 text-right tabular-nums">{Math.round((r.band.hit_rate_13w ?? 0) / 10)} von 10</td>
                <td className="py-2 pl-4 text-right tabular-nums">{r.band.median_13w != null ? pct(r.band.median_13w) : "—"}</td>
                <td className={cn("py-2 pl-4 text-right tabular-nums", r.band.episodes < THIN_EVIDENCE_EPISODES ? "text-amber-300/90" : "text-muted-foreground")}>
                  {r.band.episodes}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
        Gleiche Rechnung wie oben, nur mit anderen Kursen. Über den ganzen Zeitraum trennen die Zonen bei Aktien deutlich
        {rank(benchmarks, "SPY")}, bei der Mischung ähnlich{rank(benchmarks, "MIX6040")}, bei Gold{rank(benchmarks, "GLD")} und
        Anleihen{rank(benchmarks, "IEF")} dagegen praktisch nicht. Das Modell misst das Umfeld für Aktien, nicht für alles.
      </p>
    </div>
  );
}

/** Die gemessene Trennschärfe einer Anlage, als knapper Einschub im Fließtext. */
function rank(benchmarks: BenchmarkResult[], key: string): string {
  const ic = benchmarks.find((b) => b.key === key)?.ic_13w;
  return ic == null ? "" : ` (${ic > 0 ? "+" : ""}${ic.toFixed(2)})`;
}

/**
 * Antwort auf die Frage, ob das Modell immer gleich gut war: Es war es nicht.
 *
 * Trefferquoten je Zone taugen dafür nicht. In einem steigenden Markt sind sie überall hoch, auch wenn die
 * Reihenfolge der Zonen gar nicht stimmt. Gemessen wird deshalb, wie stark der Rang überhaupt mit dem
 * folgenden Ertrag zusammenhängt.
 */
function EraNote({ early, late }: { early: BenchmarkResult; late: BenchmarkResult }) {
  if (early.ic_13w == null || late.ic_13w == null) return null;
  const word = (ic: number) => (ic >= 0.3 ? "deutlich" : ic >= 0.15 ? "erkennbar" : "kaum");
  const earlyYear = new Date(early.start).getFullYear();
  const lateYear = new Date(late.start).getFullYear();
  return (
    <p className="max-w-3xl rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-relaxed text-pretty">
      <span className="font-medium text-amber-200">Das Modell war nicht immer gleich gut.</span>{" "}
      Wie stark die Zonen den folgenden Ertrag überhaupt getrennt haben, unterscheidet sich stark nach Zeitraum: von{" "}
      {earlyYear} bis {lateYear - 1} <strong>{word(early.ic_13w)}</strong> ({early.ic_13w.toFixed(2)}), ab {lateYear}{" "}
      <strong>{word(late.ic_13w)}</strong> ({late.ic_13w.toFixed(2)}). Der größte Teil der Aussagekraft stammt aus den
      späteren Jahren. Ob das am veränderten Umfeld liegt oder an Zufall, lässt sich mit einem einzigen Marktzyklus nicht
      entscheiden.
    </p>
  );
}
