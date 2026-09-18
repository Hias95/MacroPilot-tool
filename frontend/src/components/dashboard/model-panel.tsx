"use client";

import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { fetchHealth, type ModelCard } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Stufe D1, D3 und D6 an einer Stelle.
 *
 * D1: "Drei Treiber, drei Overlays" klingt breit. Tatsächlich bestimmt eine einzige Zeitreihe gut ein Viertel
 * des Gesamtscores und die Notenbankbilanzen zusammen deutlich mehr als vier Zehntel. Wer das nicht weiß,
 * hält das Modell für diversifizierter, als es ist.
 * D3: Der Rang misst gegen ein wanderndes Zehn-Jahres-Fenster, der Maßstab verschiebt sich also mit der Zeit.
 * D6: Welche Parameter gelten, stand bisher nur in der Git-Historie.
 */
export function ModelPanel() {
  const [card, setCard] = useState<ModelCard | null | undefined>(undefined);

  useEffect(() => {
    let alive = true;
    fetchHealth()
      .then((h) => alive && setCard(h.model ?? null))
      .catch(() => alive && setCard(null));
    return () => {
      alive = false;
    };
  }, []);

  if (!card) return null;
  const max = Math.max(...card.concentration.map((r) => r.share), 0.01);
  const years = Math.round(card.rank_window_weeks / 52);

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <Layers className="size-3.5" />
            Woran der Score wirklich hängt
          </h2>
          <span className="font-mono text-[11px] text-muted-foreground/70">
            {card.version} · Parameter {card.parameters_hash}
          </span>
        </div>

        {/* Die Einordnung wird aus den Zahlen abgeleitet. Fest hineingeschrieben stand hier "vor allem ein
            Liquiditaetsmodell"; nach der Umgewichtung auf 40/15/45 stimmte das nicht mehr, ohne dass es
            aufgefallen waere. */}
        <p className="max-w-3xl text-sm leading-relaxed text-pretty">
          Drei Treiber klingen breit. Tatsächlich bestimmt <strong className="font-semibold">{card.concentration[0]?.label}</strong>{" "}
          allein <strong className="font-semibold">{Math.round((card.concentration[0]?.share ?? 0) * 100)} Prozent</strong> des
          Gesamtscores, und die Notenbankbilanzen zusammen{" "}
          <strong className="font-semibold">{Math.round(card.central_bank_share * 100)} Prozent</strong>.{" "}
          {card.central_bank_share >= 0.4 || (card.concentration[0]?.share ?? 0) >= 0.25
            ? "Das Modell ist damit vor allem ein Liquiditätsmodell."
            : "Kein einzelner Treiber beherrscht den Score, die Notenbankbilanzen bleiben aber der größte zusammenhängende Block."}
        </p>

        <ul className="flex flex-col gap-1">
          {card.concentration.map((r) => (
            <li key={`${r.pillar}-${r.label}`} className="grid grid-cols-[minmax(0,13rem)_1fr_3rem] items-center gap-3 text-sm">
              <span className="truncate">{r.label}</span>
              <span className="h-1.5 overflow-hidden rounded-full bg-white/8" aria-hidden>
                <span className={cn("block h-full rounded-full", r.share >= 0.2 ? "bg-amber-300/80" : "bg-white/35")}
                      style={{ width: `${(r.share / max) * 100}%` }} />
              </span>
              <span className="text-right tabular-nums text-muted-foreground">{Math.round(r.share * 100)} %</span>
            </li>
          ))}
        </ul>

        <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
          Der Rang vergleicht mit den vorangegangenen {years} Jahren. Dieser Maßstab wandert mit: Ein Rang von 71 wird heute
          gegen andere Jahre gemessen als vor fünf Jahren, und die enthielten Nullzinsen. Zonen wechseln erst nach{" "}
          {card.zone_confirm_weeks} Wochen in Folge. Die Parameterkennung oben ändert sich, sobald an Gewichten oder Schwellen
          etwas geändert wird.
        </p>
      </CardContent>
    </Card>
  );
}
