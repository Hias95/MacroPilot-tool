import { DashboardClient } from "@/components/dashboard/dashboard-client";
import { DashboardHeader } from "@/components/dashboard/header";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-5 py-8 sm:px-8 sm:py-12">
      <DashboardHeader />
      <DashboardClient />
      <footer className="mt-4 border-t border-border/60 pt-4 text-[11px] leading-relaxed text-muted-foreground/80 text-pretty">
        MacroPilot ist ein Analyse- und Lernwerkzeug und keine Anlageberatung. Alle Werte und Texte sind
        Modell-Einschätzungen auf Basis öffentlicher Daten (FRED, Marktdaten) und können fehlerhaft oder verzögert
        sein. KI-Erklärungen werden automatisch erzeugt. Anlageentscheidungen triffst du eigenverantwortlich.
      </footer>
    </main>
  );
}
