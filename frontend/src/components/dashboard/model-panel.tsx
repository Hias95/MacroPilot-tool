"use client";

import { useEffect, useState } from "react";
import { Layers } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { fetchHealth, type Calibration, type ExplainStats, type ModelCard } from "@/lib/api";
import { formatDateDe } from "@/lib/format";
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
  const [stats, setStats] = useState<ExplainStats | null>(null);
  const [calib, setCalib] = useState<Calibration | null>(null);

  useEffect(() => {
    let alive = true;
    fetchHealth()
      .then((h) => {
        if (!alive) return;
        setCard(h.model ?? null);
        setStats(h.explain_stats ?? null);
        setCalib(h.calibration ?? null);
      })
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
          Der Rang vergleicht mit den vorangegangenen {years} Jahren. Dieser Maßstab wandert mit: Ein Rang wird heute
          gegen andere Jahre gemessen als vor fünf Jahren, und die enthielten Nullzinsen. Zonen wechseln erst nach{" "}
          {card.zone_confirm_weeks} Wochen in Folge.
        </p>

        {/* F3: Ohne Datum steht die Parameterkennung in der Luft. Und der Verlauf oben zeigt nicht, was das
            Werkzeug damals angezeigt hat, sondern was es mit den heutigen Parametern angezeigt hätte. */}
        {card.changes?.length ? (
          <div className="flex flex-col gap-1.5">
            <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Was wann geändert wurde</h3>
            <ul className="flex flex-col gap-1 text-xs">
              {card.changes.map((c) => (
                <li key={`${c.date}-${c.what}`} className="flex gap-3 text-pretty">
                  <span className="w-20 shrink-0 font-mono tabular-nums text-muted-foreground">{formatDateDe(c.date)}</span>
                  <span>
                    <span className="text-foreground/90">{c.what}.</span>{" "}
                    <span className="text-muted-foreground">{c.why}.</span>
                  </span>
                </li>
              ))}
            </ul>
            {card.history_recomputed ? (
              <p className="text-[11px] leading-relaxed text-amber-300/90 text-pretty">
                Wichtig dabei: Der lange Verlauf oben ist mit den heutigen Parametern nachgerechnet. Er zeigt, was das Werkzeug
                heute über die Vergangenheit sagt, nicht was es damals angezeigt hat. Erst die Tagesbilder halten das
                tatsächlich Gezeigte fest.
              </p>
            ) : null}
          </div>
        ) : null}

        {/* G2: Die eigene Trefferbilanz. Solange nichts ausgewertet werden kann, sagt sie genau das,
            statt die Lücke zu verschweigen. */}
        {calib && calib.logged > 0 ? (
          <p className="max-w-3xl text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
            <span className="text-foreground/90">Eigene Trefferbilanz:</span>{" "}
            {calib.matured > 0 && calib.actual_rate != null && calib.stated_avg != null
              ? `Von ${calib.matured} überprüfbaren Aussagen sind ${calib.hits} eingetroffen. Behauptet wurden im Schnitt ${calib.stated_avg} Prozent, tatsächlich waren es ${calib.actual_rate} Prozent.`
              : `${calib.logged} ${calib.logged === 1 ? "Aussage ist" : "Aussagen sind"} protokolliert, aber noch keine alt genug. Jede Aussage gilt für 13 Wochen, die erste Auswertung ist ab dem ${calib.due_from ? new Date(calib.due_from).toLocaleDateString("de-DE") : "?"} möglich.`}
          </p>
        ) : null}

        {/* F4: Ein stiller Rückfall auf regelbasierte Texte blieb sonst unbemerkt. */}
        {stats && stats.ready + stats.fallback > 0 ? (
          <p className={cn("text-[11px] leading-relaxed text-pretty", stats.ready === 0 ? "text-amber-300/90" : "text-muted-foreground/80")}>
            Erklärtexte im letzten Lauf: {stats.ready} vom Sprachmodell, {stats.fallback} regelbasiert
            {stats.ready > 0 && stats.used_model ? `, Modell ${stats.used_model}` : ""}
            {stats.fallback > 0 && stats.reason ? `. Grund für den Rückfall: ${stats.reason}` : "."}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
