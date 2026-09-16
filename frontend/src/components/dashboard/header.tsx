import { Gauge } from "lucide-react";
import { BackendStatus } from "./backend-status";
import { ModeToggle } from "./mode-toggle";

export function DashboardHeader() {
  const today = new Intl.DateTimeFormat("de-DE", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date());

  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="flex items-center gap-3.5">
        <div className="grid size-11 place-items-center rounded-2xl bg-white/5 ring-1 ring-white/10">
          <Gauge className="size-5" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight">MacroPilot</h1>
          <p className="text-sm text-muted-foreground">Das Marktklima auf einen Blick.</p>
        </div>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="hidden sm:inline">{today}</span>
        <BackendStatus />
        <ModeToggle />
      </div>
    </header>
  );
}
