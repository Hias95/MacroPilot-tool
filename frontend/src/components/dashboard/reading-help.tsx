"use client";

import { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * B5 und B6 in einem Element: Skalenrichtung, Bedeutung des Rangs, die ungleiche Tachoskala und die
 * Bestätigungsregel. Vier Punkte, die vorher gar nicht oder nur im Profi-Modus erklärt waren. Bewusst
 * eingeklappt, damit der Einstieg ruhig bleibt und die Erklärung trotzdem dort steht, wo die Frage entsteht.
 */
const POINTS: { term: string; text: string }[] = [
  {
    term: "Die große Zahl ist keine Rendite",
    text: "Sie ist ein Rang: Sie sagt, wie gut das Umfeld im Vergleich zu den letzten zehn Jahren dasteht. 71 heißt, es war in 71 Prozent der Wochen schlechter.",
  },
  {
    term: "Hoch ist günstig",
    text: "Alle Zahlen laufen von 0 bis 100, hoch bedeutet überall Rückenwind. Bei der Bewertung ist es deshalb umgekehrt zum Alltagsgefühl: Eine niedrige Zahl heißt teuer.",
  },
  {
    term: "Die Skala ist mit Absicht ungleich",
    text: "Die Marken 10, 30, 70 und 90 sind Quantile. Die beiden äußeren Zonen kommen je nur in etwa jeder zehnten Woche vor, die mittlere in vier von zehn.",
  },
  {
    term: "Die Zone wechselt langsam",
    text: "Erst nach drei Wochen in Folge, damit sie nicht bei jedem Ausschlag springt. Deshalb kann die Nadel bereits in der Nachbarzone stehen, während das Wort noch die alte nennt.",
  },
];

export function ReadingHelp({ className }: { className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex w-fit items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-foreground"
      >
        <HelpCircle className="size-3" />
        Wie ist das zu lesen?
        <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
      </button>
      {open ? (
        <ul className="flex flex-col gap-2 rounded-lg border border-border/60 bg-white/[0.02] p-3">
          {POINTS.map((p) => (
            <li key={p.term} className="text-xs leading-relaxed text-pretty">
              <span className="font-medium text-foreground/90">{p.term}.</span>{" "}
              <span className="text-muted-foreground">{p.text}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
