"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

type Status = "checking" | "online" | "offline";

/** Status-Punkt im Header: ist das FastAPI-Backend erreichbar, sind die Keys gesetzt? */
export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const ping = () =>
      fetchHealth(controller.signal)
        .then((h) => {
          setHealth(h);
          setStatus("online");
        })
        .catch(() => {
          if (!controller.signal.aborted) setStatus("offline");
        });
    ping();
    const id = window.setInterval(ping, 30_000);
    return () => {
      controller.abort();
      window.clearInterval(id);
    };
  }, []);

  let label = "API prüfen ...";
  if (status === "offline") label = "API offline";
  if (status === "online" && health) {
    const PROVIDER_LABEL: Record<string, string> = {
      anthropic: "Claude",
      gemini: "Gemini",
      ollama: `Ollama ${health.explain_model ?? ""}`.trim(),
      template: "regelbasiert",
      none: "aus",
    };
    const source = health.mode === "static" ? "Daten aus dem täglichen Export" : "API verbunden";
    const stand = health.snapshot_date ? ` · Stand ${new Date(health.snapshot_date).toLocaleDateString("de-DE")}` : "";
    label = `${source}${stand} · Erklärung: ${PROVIDER_LABEL[health.explain_provider] ?? health.explain_provider}`;
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-white/3 px-2.5 py-1 text-[11px] text-muted-foreground">
      <span
        className={cn(
          "size-1.5 rounded-full",
          status === "online" && "bg-emerald-400 shadow-[0_0_8px_theme(colors.emerald.400)]",
          status === "offline" && "bg-rose-400",
          status === "checking" && "bg-amber-300 animate-pulse",
        )}
      />
      {label}
    </span>
  );
}
