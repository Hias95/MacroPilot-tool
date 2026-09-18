"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { BacktestResponse } from "@/lib/api";
import { liveVariant, loadBacktest } from "@/lib/backtest";

/**
 * H1 und H3: dieselbe Wahrheit wie im Profi-Modus, in kürzeren Worten.
 *
 * Der Einfach-Modus war durchgehend die zuversichtlichere Fassung. Der Hinweis, dass das Modell bis 2018
 * kaum getrennt hat, und das Ergebnis der Zonenregeln standen nur im Profi-Modus. Genau die Einschränkungen,
 * die dem erfahrenen Leser Vertrauen geben, fehlten dem Einsteiger, der sie am wenigsten selbst mitdenken
 * kann. Hier stehen sie ohne Zahlen, aber ohne Abschwächung.
 */
export function EasyHonesty() {
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

  if (!data) return null;
  const variant = liveVariant(data);
  const early = data.early_window;
  const late = data.test_window;

  const points: string[] = [];
  if (early?.ic_13w != null && late?.ic_13w != null && early.ic_13w < late.ic_13w - 0.1) {
    const untilYear = new Date(late.start).getFullYear() - 1;
    points.push(
      `In den Jahren bis ${untilYear} hat dieses Modell kaum funktioniert. Erst danach trifft es besser. Ob das so bleibt, weiß niemand.`,
    );
  }
  if (variant) {
    const saved = variant.strategy_base.max_drawdown_pct - variant.buy_hold.max_drawdown_pct;
    points.push(
      saved < 1
        ? "Wer den Zonen gefolgt wäre, hätte im Rückblick Rendite verloren und beim größten Absturz trotzdem nichts gespart. Ruhiger heißt nicht sicherer."
        : "Wer den Zonen gefolgt wäre, hätte im Rückblick Rendite verloren und dafür einen etwas kleineren Absturz gehabt.",
    );
  }
  points.push(
    "Die Zahl misst das Umfeld für US-Aktien in den nächsten drei Monaten. Sie sagt nichts über deine Anlagen und nichts über morgen.",
  );
  if (points.length === 0) return null;

  return (
    <Card className="border-amber-400/20 bg-amber-400/[0.04] ring-0">
      <CardContent className="flex flex-col gap-2 py-1">
        <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-amber-200/90">
          <ShieldAlert className="size-3.5" />
          Was du über dieses Modell wissen solltest
        </h2>
        <ul className="flex flex-col gap-1.5">
          {points.map((t) => (
            <li key={t} className="text-sm leading-relaxed text-pretty text-foreground/90">
              {t}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
