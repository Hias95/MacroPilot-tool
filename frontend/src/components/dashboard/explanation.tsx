"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchExplanation, type ExplanationResponse, type PillarId } from "@/lib/api";
import { formatDateTimeDe } from "@/lib/format";

type State =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; data: ExplanationResponse };

interface Props {
  pillarId: PillarId;
  /** Aendert sich nur mit den Daten; loest dann eine neue Erklaerung aus. */
  fingerprint: string;
  accent: string;
}

/** KI-Erklaerung: warum der Score so aussieht, in einfachen Worten. */
export function Explanation({ pillarId, fingerprint, accent }: Props) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchExplanation(pillarId, controller.signal)
      .then((data) => setState({ status: "done", data }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: err instanceof Error ? err.message : String(err) });
      });
    return () => controller.abort();
  }, [pillarId, fingerprint, attempt]);

  const retry = () => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  };

  return (
    <div className="rounded-lg border border-border/60 bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        <Sparkles className="size-3" style={{ color: accent }} />
        Warum dieser Score?
      </div>

      {state.status === "loading" ? (
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-11/12" />
          <Skeleton className="h-3 w-4/6" />
        </div>
      ) : null}

      {state.status === "done" && state.data.status === "ready" ? (
        <>
          <p className="text-sm leading-relaxed text-foreground/90 text-pretty">{state.data.text}</p>
          <div className="mt-2 text-[10px] leading-relaxed text-muted-foreground/70">
            {state.data.provider === "template" ? "Regelbasierte Erklärung" : `KI-Erklärung · ${state.data.model}`}
            {state.data.generated_at ? ` · ${formatDateTimeDe(state.data.generated_at)}` : ""}
            {state.data.reason ? <span className="block">KI nicht verfügbar ({state.data.reason})</span> : null}
          </div>
        </>
      ) : null}

      {state.status === "done" && state.data.status === "unavailable" ? (
        <p className="text-xs leading-relaxed text-muted-foreground text-pretty">
          KI-Erklärung nicht verfügbar: {state.data.reason}
        </p>
      ) : null}

      {state.status === "error" ? (
        <div className="text-xs text-muted-foreground">
          <p className="text-pretty">{state.message}</p>
          <Button variant="outline" size="sm" className="mt-2 h-7 gap-1.5 text-xs" onClick={retry}>
            <RefreshCw className="size-3" />
            Erneut versuchen
          </Button>
        </div>
      ) : null}
    </div>
  );
}
