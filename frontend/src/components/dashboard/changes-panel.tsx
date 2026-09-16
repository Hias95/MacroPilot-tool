"use client";

import { useEffect, useState } from "react";
import { Bell } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { fetchChanges, type ChangeEvent } from "@/lib/api";
import { formatDateDe } from "@/lib/format";
import { cn } from "@/lib/utils";

const KIND_LABEL: Record<ChangeEvent["kind"], string> = {
  zone: "Zone",
  phase: "Phase",
  regime: "Regime",
  confirmation: "Markt",
  veto: "Veto",
};
const KIND_TONE: Record<ChangeEvent["kind"], string> = {
  zone: "border-sky-400/40 text-sky-300",
  phase: "border-violet-400/40 text-violet-300",
  regime: "border-amber-400/40 text-amber-300",
  confirmation: "border-emerald-400/40 text-emerald-300",
  veto: "border-rose-400/40 text-rose-300",
};

/** Was hat sich geaendert? Erkannte Wechsel aus den Tagesbildern (D1/D3), gleiche Liste wie die Benachrichtigungen. */
export function ChangesPanel({ days = 90, compact = false }: { days?: number; compact?: boolean }) {
  const [events, setEvents] = useState<ChangeEvent[] | null | undefined>(undefined);
  const [meta, setMeta] = useState<{ snapshot_date: string | null; last_refresh: string | null } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchChanges(days, controller.signal)
      .then((c) => {
        setEvents(c.events);
        setMeta({ snapshot_date: c.snapshot_date, last_refresh: c.last_refresh });
      })
      .catch(() => {
        if (!controller.signal.aborted) setEvents(null);
      });
    return () => controller.abort();
  }, [days]);

  if (events === null) return null;
  const shown = compact ? (events ?? []).slice(0, 5) : (events ?? []);

  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <Bell className="size-3.5" />
            Was hat sich geändert? Letzte {days} Tage
          </h2>
          {meta?.snapshot_date ? (
            <span className="text-[11px] text-muted-foreground/80">
              Tagesbild vom {formatDateDe(meta.snapshot_date)}
              {meta.last_refresh ? ` · Refresh ${new Date(meta.last_refresh).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" })}` : ""}
            </span>
          ) : null}
        </div>
        {events === undefined ? <p className="text-xs text-muted-foreground">Lade Änderungen ...</p> : null}
        {events && events.length === 0 ? (
          <p className="text-sm text-muted-foreground text-pretty">
            Keine Wechsel erkannt. Das Tool merkt sich jeden Tag ein Bild des Dashboards und meldet hier, wenn Zone, Zyklusphase, ein Regime-Flag, die Marktbestätigung oder ein Veto wechselt.
          </p>
        ) : null}
        {shown.length > 0 ? (
          <ul className="flex flex-col divide-y divide-border/60">
            {shown.map((e) => (
              <li key={e.id} className="flex gap-3 py-2 text-sm">
                <span className="w-20 shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">{formatDateDe(e.date)}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wider", KIND_TONE[e.kind])}>{KIND_LABEL[e.kind]}</span>
                    <span className="font-medium">{e.title}</span>
                  </div>
                  {!compact ? <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground text-pretty">{e.detail}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
        {compact && events && events.length > 5 ? <p className="text-[11px] text-muted-foreground">{events.length - 5} weitere im Profi-Modus.</p> : null}
      </CardContent>
    </Card>
  );
}
