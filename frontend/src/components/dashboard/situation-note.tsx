"use client";

import { useEffect, useState } from "react";
import { UserRound } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestBand, BacktestResponse, ZoneKey } from "@/lib/api";
import { bandFor, liveVariant, loadBacktest } from "@/lib/backtest";
import { formatDe } from "@/lib/format";
import { SITUATIONS, setSituation, useSituation, type Situation } from "@/lib/situation";
import { cn } from "@/lib/utils";

/**
 * I1: Dieselben Daten, eingeordnet in die Lage des Lesers.
 *
 * Bewusst keine Empfehlung. Jeder Satz beschreibt nur, wie die eigene Methode auf den Zeitpunkt reagiert,
 * und das ist Arithmetik, keine Marktmeinung. Wer monatlich kauft, verteilt den Zeitpunkt über hunderte
 * Käufe; wer alles auf einmal anlegt, tut das nicht. Diese Unterscheidung fehlte bisher vollständig, und
 * dadurch bekam die Sparplan-Anlegerin eine Antwort auf eine Frage, die sie gar nicht hat.
 */
function text(situation: Situation, band: BacktestBand | null, drawdown: number | null): string {
  if (situation === "plan") {
    return (
      "Beim monatlichen Sparen betrifft ein einzelner Kaufzeitpunkt nur einen kleinen Teil deiner Summe. " +
      "Ob das Umfeld heute günstig oder ungünstig ist, verschiebt dein Ergebnis deshalb kaum. Wichtiger ist, " +
      "dass du die Raten auch dann weiterlaufen lässt, wenn die Zahl oben tief steht."
    );
  }
  if (situation === "lump") {
    const range =
      band?.p10_fwd_13w != null && band?.p90_fwd_13w != null
        ? `Nach Wochen wie dieser lag der Index drei Monate später meist zwischen ${formatDe(band.p10_fwd_13w, 0)} und ${formatDe(band.p90_fwd_13w, 0)} Prozent gegenüber heute. `
        : "";
    return (
      "Wenn du alles auf einmal anlegst, zählt der Zeitpunkt tatsächlich, weil deine ganze Summe zum selben " +
      `Kurs gekauft wird. ${range}` +
      "Die Spanne ist dabei die ehrlichere Angabe als der Mittelwert. Wer sie nicht aushalten will, kann die " +
      "Summe auch über mehrere Monate verteilen; das verringert die Spanne, nicht die Rendite-Erwartung."
    );
  }
  const dd = drawdown != null ? `Der tiefste Rückgang im Rückblick lag bei ${formatDe(drawdown, 0)} Prozent. ` : "";
  return (
    "Für ein bestehendes Depot ist die Frage selten, ob du kaufst, sondern ob du die Schwankung aushältst, " +
    `die dazugehört. ${dd}` +
    "Die Zonenregeln aus dem Rückblick haben daran nichts geändert: Sie kosteten Rendite und verhinderten den " +
    "tiefsten Rückgang nicht."
  );
}

export function SituationNote({ zone }: { zone: ZoneKey }) {
  const situation = useSituation();
  const [data, setData] = useState<BacktestResponse | null>(null);

  useEffect(() => {
    let alive = true;
    loadBacktest()
      .then((res) => alive && setData(res))
      .catch(() => alive && setData(null));
    return () => {
      alive = false;
    };
  }, []);

  const variant = data ? liveVariant(data) : null;
  const band = variant ? bandFor(variant, zone) : null;
  const drawdown = variant?.buy_hold.max_drawdown_pct ?? null;

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <UserRound className="size-3.5" />
            Was heißt das für dich?
          </h2>
          <div role="group" aria-label="Deine Lage" className="inline-flex rounded-lg border border-border/70 p-0.5">
            {SITUATIONS.map((s) => (
              <button
                key={s.key}
                type="button"
                onClick={() => setSituation(s.key)}
                aria-pressed={situation === s.key}
                title={s.label}
                className={cn(
                  "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                  situation === s.key ? "bg-white/10 text-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {s.short}
              </button>
            ))}
          </div>
        </div>
        <p className="max-w-3xl text-sm leading-relaxed text-pretty">{text(situation, band, drawdown)}</p>
        <p className="text-[11px] text-muted-foreground/70">
          Das ist keine Empfehlung, sondern eine Einordnung deiner Methode. Die Zahlen oben bleiben für alle gleich.
        </p>
      </CardContent>
    </Card>
  );
}
