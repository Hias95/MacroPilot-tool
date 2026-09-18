import { Card, CardContent } from "@/components/ui/card";
import { CircleOff } from "lucide-react";

/**
 * B2: Worüber das Tool nichts sagt.
 *
 * Der Haftungshinweis am Seitenende sagt, dass es keine Beratung ist. Er sagt nicht, was schlicht ausserhalb
 * des Modells liegt. Genau daraus entstehen aber die Fehlschluesse: Wer ein Welt-Portfolio haelt, liest hier
 * eine Aussage ueber den US-Aktienmarkt in Dollar und bezieht sie auf etwas anderes.
 */
const LIMITS: { title: string; text: string }[] = [
  { title: "Einzelne Anlagen", text: "Aktien, Anleihen, Gold, Krypto und Immobilien kommen im Modell nicht vor." },
  { title: "Andere Regionen", text: "Gemessen wird das Umfeld für den US-Aktienmarkt. Europa und Schwellenländer laufen oft anders." },
  { title: "Deine Währung", text: "Alle Zahlen sind in Dollar. Wer in Euro rechnet, trägt zusätzlich das Wechselkursrisiko." },
  { title: "Deine Lage", text: "Anlagehorizont, Steuern, Notgroschen, Schulden und Risikotragfähigkeit kennt das Tool nicht." },
  { title: "Die nächsten Tage", text: "Der Horizont des Modells sind drei bis sechs Monate. Über morgen sagt es nichts." },
];

export function LimitsPanel() {
  return (
    <Card className="bg-card ring-white/8">
      <CardContent className="flex flex-col gap-3 py-1">
        <h2 className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <CircleOff className="size-3.5" />
          Worüber dieses Tool nichts sagt
        </h2>
        <ul className="grid grid-cols-1 gap-x-8 gap-y-2 sm:grid-cols-2 xl:grid-cols-3">
          {LIMITS.map((l) => (
            <li key={l.title} className="text-sm leading-relaxed text-pretty">
              <span className="font-medium">{l.title}.</span>{" "}
              <span className="text-muted-foreground">{l.text}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
