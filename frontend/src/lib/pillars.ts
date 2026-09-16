/** UI-Metadaten der Saeulen (drei Treiber, drei Overlays). Name, Beschreibung und Daten kommen vom Backend. */

import type { PillarId } from "./api";

export interface PillarUi {
  /** Akzentfarbe (CSS-Farbe) */
  accent: string;
  /** Erklaerung fuer die Info-Flaeche: was steckt dahinter, in einfachen Worten */
  explainer: string;
  /** Wie man den Score dieser Saeule liest */
  reading: string;
}

export const PILLAR_UI: Record<PillarId, PillarUi> = {
  liquidity: {
    accent: "oklch(0.8 0.13 215)",
    explainer:
      "Geld bewegt Märkte, sagt Michael Howell. Drei Signale zeigen, wie viel davon gerade fließt. Net Liquidity: Was von der Fed-Bilanz übrig bleibt, nachdem das Finanzministerium Geld auf seinem Konto parkt und Fonds Geld über Nacht bei der Fed abstellen. Notenbanken global: Fed, EZB und Bank of Japan zusammen in Dollar, weil Kapital keine Grenzen kennt. T-Bill-Anteil: Finanziert sich der Staat kurzfristig, holen Geldmarktfonds ihr Geld von der Fed zurück und schieben es in den Markt.",
    reading:
      "Hoher Score: Es kommt netto Geld ins System, Rückenwind für Risiko. Niedriger Score: Geld wird abgezogen, Gegenwind.",
  },
  cycle: {
    accent: "oklch(0.74 0.16 300)",
    explainer:
      "Jeden Monat fragen die regionalen Notenbanken in Philadelphia, New York und Dallas Industriefirmen, ob ihre Geschäfte gerade besser oder schlechter laufen. Der Wert ist der Anteil der Optimisten minus Anteil der Pessimisten: über null wächst die Industrie, unter null schrumpft sie. Der Durchschnitt dieser Umfragen läuft eng mit dem bekannten ISM-Index, den Raoul Pal als Taktgeber für Gewinne und Kurse nutzt.",
    reading: "Hoher Score: Die Wirtschaft beschleunigt. Niedriger Score: Sie bremst. Die Wende zählt mehr als das Niveau.",
  },
  markets: {
    accent: "oklch(0.83 0.15 80)",
    explainer:
      "Vier Signale zeigen, was das große Geld gerade tut: Laufen viele Aktien mit oder nur wenige Riesen (Breite)? Suchen Anleger weltweit Risiko oder Sicherheit (Australischer Dollar gegen Yen)? Erwartet die Industrie Wachstum (Kupfer gegen Gold)? Vertrauen Anleger riskanten Firmenanleihen (High Yield gegen Staatsanleihen)? Der Backtest zeigt: Diese Preise laufen dem Markt nach, nicht voraus, deshalb treiben sie den Consensus nicht. Sie bestätigen ihn oder widersprechen ihm, und an Extremen kippt ihre Bedeutung: Ausverkauf war historisch Wendepunkt.",
    reading: "Bestätigt der Markt das Makrobild, war die Lage historisch am verlässlichsten. Läuft der Markt dem Makrobild voraus, war das die schwächste Kombination. Unter 30 gilt Marktstress (Rückschläge verstärken sich), unter 20 Kapitulation.",
  },
  structure: {
    accent: "oklch(0.74 0.17 15)",
    explainer:
      "Diese Säule fragt, wie viel Spielraum das System noch hat. Zinskurve: Zahlen kurze Anleihen mehr als lange, war das fast immer ein Vorbote einer Rezession, und die Versteilung danach ist das akute Signal. Realzins: Je höher der Zins nach Inflation, desto teurer wird Kapital. Kerninflation: Über zwei Prozent kann die Notenbank in einer Krise weniger helfen. Dazu zwei Schuldenmaße: Wie viel Einkommen die Haushalte für Zins und Tilgung brauchen, und wie viel der Steuereinnahmen der Staat allein für Zinsen ausgibt. Ray Dalio denkt in solchen Schuldenzyklen, Russell Napier beschreibt, was passiert, wenn der Staat die Notenbank dominiert.",
    reading: "Hoher Score: Viel Spielraum, wenig strukturelle Risiken. Niedriger Score: Das Fundament ist angeschlagen. Der Regime-Check zeigt, ob der Staat die Geldpolitik bereits dominiert.",
  },
  mechanics: {
    accent: "oklch(0.78 0.1 190)",
    explainer:
      "Ein großer Teil des Handels läuft heute über Algorithmen, die ihre Aktienquote an der Schwankung ausrichten, und über Optionshändler, die ihre Bücher absichern müssen. Solange die Volatilität niedrig ist, kaufen diese Maschinen und dämpfen jede Bewegung. Springt sie, verkaufen sie mechanisch, egal was die Wirtschaft macht. Die echten Positionsdaten sind kostenpflichtig; VIX, VIX-Terminstruktur und SKEW zeigen dieselbe Mechanik von außen.",
    reading:
      "Hoher Score: ruhige Technik, Rückschläge werden gekauft. Niedriger Score: die Maschinen stehen auf Verkaufen, kurzfristig Kaskadengefahr. In der Panik-Zone gilt das Gegenteil: Extreme Angst war historisch eher Kaufzone.",
  },
  valuation: {
    accent: "oklch(0.8 0.12 320)",
    explainer:
      "Bewertung sagt wenig darüber, wohin der Markt in den nächsten Monaten läuft, aber viel darüber, wie tief es geht, wenn etwas schiefläuft. Deshalb ist sie kein Treiber der Jahreszeit, sondern misst die Fallhöhe. Drei Maße: Der Shiller-CAPE setzt den Kurs ins Verhältnis zum inflationsbereinigten Gewinn der letzten zehn Jahre. Die Risikoprämie zeigt, was Aktien nach Abzug des sicheren Realzinses mehr abwerfen. Der Buffett-Indikator vergleicht den Wert aller US-Aktien mit der Wirtschaftsleistung.",
    reading:
      "Hoher Score: günstig, viel Sicherheitspuffer, Rückschläge werden absorbiert. Niedriger Score: teuer, große Fallhöhe, kleine Enttäuschungen kosten viel. Der Regime-Check zeigt, ob der Markt Perfektion einpreist.",
  },
};

export const PILLAR_ORDER: PillarId[] = ["liquidity", "cycle", "structure"];
