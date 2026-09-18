"use client";

import { useEffect, useState } from "react";
import { Telescope } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestBand, BenchmarkBand, ConditionalBand, ZoneKey } from "@/lib/api";
import { CONDITION_MATTERS_PP, OUTLOOK_LABEL, THIN_EVIDENCE_EPISODES, bandFor, conditionalFor, liveVariant, loadBacktest, zoneBandOf } from "@/lib/backtest";
import { cn } from "@/lib/utils";

// Genau zehn Punkte, damit der Streifen eins zu eins zum Satz "X von 10" passt. Eine feinere Aufloesung
// waere genauer, aber der Leser muesste zwischen zwei Zahlen umrechnen, und genau das soll er nicht.
const DOTS = 10;

interface Loaded {
  band: BacktestBand;
  benchmark: string;
  startYear: number;
  /** Paare aus heutiger Bedingung und ihrem Gegenstueck, fuer den Vergleich "mit gegen ohne". */
  conditions: { now: ConditionalBand; other: ConditionalBand | null; intro: string }[];
  /** Dieselbe Zone ausserhalb des Kalibrierzeitraums. Gehoert in die Grundlagenzeile, nicht in eine eigene. */
  test: { band: BenchmarkBand; fromYear: number } | null;
}

/**
 * Der Erwartungssatz: uebersetzt den Rang in eine Aussage mit Bezugsklasse, Zeitraum und Spannweite.
 *
 * Form und Wortwahl folgen der Risikokommunikation: natuerliche Haeufigkeit statt Prozentsatz
 * ("8 von 10"), die Bezugsklasse ausdruecklich genannt ("Wochen wie diese"), der Zeitraum immer dabei,
 * und ein abzaehlbarer Streifen statt einer glatten Kurve. Alle Zahlen stammen aus abgezaehlter Historie,
 * nichts ist modelliert.
 */
interface Props {
  zoneKey: ZoneKey;
  zoneLabel: string;
  zoneColor: string;
  /** Ist der Markt heute extrem teuer? Dann zaehlt nur, wie solche Wochen ausgingen. */
  valuationExtreme?: boolean;
  /** Bestaetigt der Markt heute das Makrobild? null, wenn unbekannt. */
  marketConfirmed?: boolean | null;
}

export function OutlookPanel({ zoneKey, zoneLabel, zoneColor, valuationExtreme, marketConfirmed }: Props) {
  const [data, setData] = useState<Loaded | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    loadBacktest()
      .then((res) => {
        const variant = liveVariant(res);
        const band = variant ? bandFor(variant, zoneKey) : null;
        if (!alive) return;
        // Nur die Bedingungen, die heute zutreffen. Was waere, wenn der Markt guenstig waere, interessiert nicht.
        const wanted: [ConditionalBand["condition"], ConditionalBand["condition"], string][] = [];
        if (valuationExtreme) wanted.push(["valuation_extreme", "valuation_other", "War der Markt dabei extrem teuer, wie jetzt"]);
        if (marketConfirmed === true) wanted.push(["market_confirmed", "market_other", "Bestätigte der Markt dabei das Bild, wie jetzt"]);
        if (marketConfirmed === false) wanted.push(["market_other", "market_confirmed", "Bestätigte der Markt dabei das Bild nicht, wie jetzt"]);
        const conditions = wanted
          .map(([now, other, intro]) => ({ now: conditionalFor(res, zoneKey, now), other: conditionalFor(res, zoneKey, other), intro }))
          .filter((c): c is { now: ConditionalBand; other: ConditionalBand | null; intro: string } => c.now != null && c.now.hit_rate_13w != null);
        const testBand = zoneBandOf(res.test_window, zoneKey);
        const test = testBand && testBand.hit_rate_13w != null && res.test_window
          ? { band: testBand, fromYear: new Date(res.test_window.start).getFullYear() }
          : null;
        setData(band && variant
          ? { band, benchmark: res.benchmark, startYear: new Date(variant.start).getFullYear(), conditions, test }
          : null);
      })
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, [zoneKey, valuationExtreme, marketConfirmed]);

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

function Outlook({ band, benchmark, startYear, conditions, test, zoneLabel, zoneColor }: Loaded & { zoneLabel: string; zoneColor: string }) {
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
          Ein Punkt steht für eine von zehn vergleichbaren Wochen. Grün heißt: Der Index stand {OUTLOOK_LABEL} später höher.
        </p>
      </div>

      {band.p50_fwd_13w != null ? (
        <p className="max-w-3xl text-base leading-relaxed text-pretty">
          Meistens ging es um {Math.abs(Math.round(band.p50_fwd_13w))} Prozent nach{" "}
          {band.p50_fwd_13w >= 0 ? "oben" : "unten"}
          {band.p10_fwd_13w != null && band.p10_fwd_13w < 0
            ? `, in den schlechten Fällen um ${Math.abs(Math.round(band.p10_fwd_13w))} Prozent nach unten`
            : ""}
          .
        </p>
      ) : null}

      {conditions.length > 0 ? (
        <div className="flex flex-col gap-1.5">
          {conditions.map((c) => (
            <ConditionLine key={c.now.condition} {...c} />
          ))}
        </div>
      ) : null}

      <p className={cn("max-w-3xl text-[11px] leading-relaxed text-pretty", thin ? "text-amber-300/90" : "text-muted-foreground/80")}>
        {thin
          ? `So etwas gab es seit ${startYear} aber nur ${band.episodes} Mal. Das ist zu selten, um daraus viel abzuleiten.`
          : `Gezählt über ${band.episodes} solcher Phasen seit ${startYear}.`}{" "}
        {/* C2: Die Gewichte wurden auf Daten bis Ende 2018 gesucht. Nur die Jahre danach sind unverbraucht. */}
        {test
          ? `Rechnet man nur die Jahre ab ${test.fromYear}, die bei der Kalibrierung nicht verwendet wurden: ` +
            `${Math.round((test.band.hit_rate_13w ?? 0) / 10)} von 10 aus ${test.band.episodes} ` +
            `${test.band.episodes === 1 ? "Phase" : "Phasen"}. `
          : ""}
        Das ist ein Rückblick, keine Vorhersage.
      </p>
    </>
  );
}

/**
 * Was die heutige Zusatzbedingung an der Erwartung ändert.
 *
 * Verglichen wird nicht gegen den Durchschnitt aller Wochen, sondern gegen das Gegenstück: mit Bestätigung
 * gegen ohne. Nur so beantwortet der Satz die Frage, die er stellt. Ändert sich wenig, sagt er auch das,
 * denn "die Bewertung hat daran historisch nichts geändert" ist eine Information und keine Leerstelle.
 */
function ConditionLine({ now, other, intro }: { now: ConditionalBand; other: ConditionalBand | null; intro: string }) {
  const hit = now.hit_rate_13w;
  if (hit == null) return null;
  const mine = Math.round(hit / 10);
  const theirs = other?.hit_rate_13w != null ? Math.round(other.hit_rate_13w / 10) : null;
  const matters = other?.hit_rate_13w != null && Math.abs(hit - other.hit_rate_13w) >= CONDITION_MATTERS_PP;
  const thin = now.episodes > 0 && now.episodes < THIN_EVIDENCE_EPISODES;

  return (
    <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground text-pretty">
      {intro}:{" "}
      <span className="font-medium text-foreground">{mine} von 10</span>
      {matters && theirs != null ? ` statt ${theirs} von 10 sonst.` : ", das hat historisch wenig geändert."}{" "}
      <span className={cn("text-[11px]", thin ? "text-amber-300/90" : "text-muted-foreground/70")}>
        {now.episodes} {now.episodes === 1 ? "Phase" : "Phasen"}
        {thin ? ", zu wenige für eine belastbare Aussage" : ""}
      </span>
    </p>
  );
}
