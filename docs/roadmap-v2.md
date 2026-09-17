# MacroPilot Roadmap v2: Vom 4-Saeulen-MVP zum kalibrierten Modell

Stand: 16.09.2026. Grundlage: Strategie-Review, das 7-Saeulen-Dokument (docs/sieben-saeulen-modell.txt,
als Inspiration) und 30 live geprueften Datenquellen. Alle Quellen sind kostenlos.

## 1. Architektur-Entscheidung: 4 Treiber, 2 Overlays, 1 Regime-Flag

Warum nicht sieben gleichberechtigte Saeulen:

- Bewertung (CAPE, ERP, Buffett) hat auf 1 bis 12 Monate praktisch keine Prognosekraft, auf 7 bis 10 Jahre
  eine hohe. 2013 bis 2021 war der Markt durchgehend teuer und lief trotzdem. Als 10 % in einer linearen
  Summe verwaessert sie das Timing-Signal. Ihre richtige Rolle ist die Fallhoehe: Wie tief geht es, wenn
  etwas schiefgeht. Deshalb Overlay mit Deckel, nicht Saeule.
- Marktmechanik (Gamma, CTAs, Volatilitaet, Sentiment) wirkt in Tagen bis drei Wochen und dreht an
  Extremen: Panik ist historisch Kaufzone. Als lineare Saeule haette sie das falsche Vorzeichen. Richtig
  ist ein Warn- und Kontra-Overlay mit kleinem Einfluss auf den Score.
- Fiskalische Dominanz ist ein Regime und ein Liquiditaetskanal, keine eigene Achse. T-Bill-Emissionen
  wirken bereits in Net Liquidity (ueber die Reverse-Repo-Fazilitaet), die Zinslast ist Strukturrisiko.
  Als eigene Saeule wuerde sie doppelt zaehlen. Deshalb Sub-Signale in Saeule 1 und 4 plus ein Regime-Flag
  "Fiskalische Dominanz aktiv" mit Sachwerte-Hinweis.

Ergebnis:

| Baustein | Rolle | Startgewicht | Wirkung |
|---|---|---|---|
| Liquiditaet | Treiber | 55 % (C2, vorher 35) | Score und Zone |
| Marktsignale (frueher Marktwahrheit) | Overlay (seit 16.09.2026, docs/marktsignale-rolle.md) | 0 % | Badge Markt bestaetigt / zoegert / laeuft voraus, Flag Marktstress / Kapitulation |
| Konjunktur | Treiber | 15 % (C2, vorher 25) | Score und Zone |
| Struktur & Fiskus | Treiber | 30 % (C2, vorher 15) | Score und Zone |
| Bewertung / Fallhoehe | Overlay | 0 % linear | Deckel nach oben, Label "Fallhoehe" |
| Marktmechanik / Volatilitaet | Overlay | 0 % linear | bis 5 Punkte als Kontra (C2: Stress hebt, Sorglosigkeit senkt), Warnung |
| Fiskalische Dominanz | Regime-Flag | 0 % | Badge, Hinweis auf Sachwerte |

Vetos (Startwerte): Liquiditaet unter 20 deckelt bei 35. Struktur unter 20 deckelt bei 30. Bewertung
extrem teuer und Mechanik gestresst deckelt bei 40. Anzeige (Entscheidung 16.09.2026 nach Backtest C1, Variante 1):
nicht der Rohwert, sondern sein Rang gegenueber den letzten zehn Jahren ("besser als X % der Wochen"), weil der
Rohwert komprimiert ist (p10 39, p90 69). Ampelzonen als Quantile des Rangs: unter 10 Stark negativ, 10 bis 30 Negativ,
30 bis 70 Neutral, 70 bis 90 Positiv, ab 90 Stark positiv. Die Zahl bleibt ungeglaettet, die Zone wechselt erst nach
drei Wochen in Folge. Frueher verworfen: Jahreszeiten (implizieren eine Reihenfolge) und feste Klima-Baender des
Rohwerts (Extreme wurden nie erreicht).
Die Investment-Clock (Richtung Liquiditaet mal Richtung Konjunktur) bleibt als Qualifier: frueh, spaet,
Erholung beginnt, Abschwung. Alle Gewichte, Lookbacks und Schwellen liegen in einer Datei
(backend/app/model_config.py), damit der Backtest sie kalibrieren kann.

## 2. Indikatoren je Baustein (Quelle, Richtung, Startgewicht)

Saeule 1 Liquiditaet
- Net Liquidity = WALCL - WTREGEN - RRPONTSYD (FRED), woechentlich, hoch = gut, 50 %
- Globaler Proxy: Fed + EZB (ECBASSETSW) + BoJ (JPNASSETS) in USD (Yahoo EURUSD, USDJPY), 30 %
- Fiskal-Impuls: Veraenderung des T-Bill-Anteils an marktfaehigen Schulden (Treasury MSPD-API), 20 %

Saeule 2 Konjunktur
- Regional-Fed-Composite Philadelphia, New York, Dallas (FRED), monatlich, 100 %
- Pals Phasenlogik als Qualifier: Tief im Kontraktionsbereich mit drehendem Momentum = Fruehling
- Spaeter optional: OECD CLI ueber die OECD-API (FRED-Serie endet 2024), ISM als manuelle Eingabe

Saeule 3 Marktwahrheit (ersetzt XLY/XLP und SMH/SPY)
- Breite RSP/SPY (Yahoo), 25 %
- Risikoappetit AUD/JPY (Yahoo AUDJPY=X), 25 %
- Realwirtschaft Kupfer/Gold (Yahoo HG=F, GC=F), 25 %
- Kredit High-Yield-Spread BAMLH0A0HYM2 (FRED), invertiert, 25 %

Saeule 4 Struktur & Fiskus
- Zinskurve T10Y2Y, 30 %, mit Un-Inversions-Regel: war die Kurve in 12 Monaten invers und steigt sie in
  3 Monaten um mehr als 0,5 Punkte, wird der Kurven-Score gedeckelt (Panik-Versteilung)
- Realzins DFII10, invertiert, 25 %
- Kerninflation CPILFESL Jahresrate, invertiert, 15 %
- Schuldendienstquote TDSP, invertiert, 15 %
- Zinslast des Bundes / Steuereinnahmen A091RC1Q027SBEA / W006RC1Q027SBEA, invertiert, 15 %

Overlay Bewertung / Fallhoehe
- Shiller CAPE, invertiert, 40 % (Quelle shillerdata.com, Parser noetig; Yale-Datei endet 2023)
- Excess CAPE Yield als Risikopraemie, 40 %
- Buffett-Indikator NCBEILQ027S / GDP (FRED, Fed-Finanzierungsrechnung), invertiert, 20 %
- Ausgabe: Score, Label (guenstig, fair, teuer, extrem), Deckel fuer den Consensus

Overlay Marktmechanik / Volatilitaet (Proxys fuer Gamma, CTAs, Cash-Quote, die alle proprietaer sind)
- VIX-Niveau (CBOE VIX_History.csv), invertiert, 40 %
- Terminstruktur VIX / VIX3M (CBOE), Backwardation = Stress, 40 %
- SKEW (Yahoo ^SKEW), Absicherungsnachfrage, 20 %
- Kontra-Regel: VIX-Perzentil ueber 90 = "Panik-Zone, historisch Kaufzone" als Hinweis

Regime-Flag Fiskalische Dominanz: aktiv, wenn zwei von drei zutreffen: Zinslast/Steuern ueber 25 %,
T-Bill-Anteil ueber 20 %, Repression (10-Jahres-Rendite minus Inflation) unter null.
Aktuell: 33 % Zinslast, 22,8 % T-Bill-Anteil, Repression +2,3 Punkte, also aktiv (2 von 3).

## 3. Score-Rechnung

Jeder Teilindikator: Perzentil des Niveaus (40 %) plus Perzentil des Momentums (60 %), beides ueber ein
Lookback-Fenster je Baustein. Perzentile statt Z-Scores, weil sie robust gegen Ausreisser sind und keine
Normalverteilung voraussetzen. Momentum bleibt im Score, weil Richtung mehr sagt als Niveau.
Lookbacks (Start): Liquiditaet 10 Jahre, Konjunktur 10 Jahre, Marktwahrheit 5 Jahre, Struktur 10 Jahre,
Bewertung 30 Jahre, Mechanik 10 Jahre. Trend-Vektor je Baustein: 4-Wochen-Veraenderung des Scores.

## 4. Plan in Reihenfolge, jeder Schritt einzeln lieferbar und pruefbar

Phase A: Modell v2
- A1 (erledigt 16.09.2026) Score-Engine als Zeitreihe: jede Saeule liefert ihren Score fuer jede Woche seit
  2003 (rollierende Fenster, kein Blick in die Zukunft), Consensus-Verlauf, Endpunkt /api/v1/history,
  Verlaufs-Chart im Panel. Nebenbefund behoben: Momentum bei Indizes und Zinsen absolut statt prozentual.
- A2 (erledigt 16.09.2026) Saeule 3 heisst jetzt Marktsignale: RSP/SPY, AUD/JPY, Kupfer/Gold (Futures,
  mal 1000), HYG/IEF als Kredit-Proxy. Zentrale Parameterdatei backend/app/model_config.py angelegt.
- A3 (erledigt 16.09.2026) Saeule 4 zu Struktur & Fiskus: fuenf gewichtete Bestandteile, Un-Inversions-Regel,
  Regime-Flag Fiskalische Dominanz, Treasury-Client, Veroeffentlichungsverzug fuer Quartals- und Monatsdaten.
- A4 (erledigt 16.09.2026) Saeule 1 erweitert: Net Liquidity 50 %, Notenbank-Proxy Fed+EZB+BoJ in USD 30 %,
  T-Bill-Anteil 20 %. Gewichtete Mittelung jetzt gemeinsam in pillars/common.py.
- A5 (erledigt 16.09.2026) Overlay Marktmechanik: VIX, VIX/VIX3M, SKEW mit Panik-Regel; Treiber und
  Overlays sind im Schema getrennt (kind), Overlays haben eine eigene Zeile im Dashboard.
- A6 (erledigt 16.09.2026) Overlay Bewertung: Shiller-Parser (shillerdata.com), Risikopraemie, Buffett ueber
  Fed Z.1, Fallhoehe-Label, Regime-Flag Extreme Bewertung.
- A7 (erledigt 16.09.2026) Consensus v2: Gewichte, Mechanik-Korrektur mit Kontra-Regel, Bewertungs-Deckel,
  Vetos, Zyklusphase mit Hysterese, Warum-Text. Klima-Baender und Glaettung am 16.09.2026 durch Rang plus Ampelzonen ersetzt.

Phase B: Easy- und Pro-Modus
- B1 (erledigt 16.09.2026) Umschalter Einfach/Profi im Header, gemerkt im Browser. Easy zeigt je Baustein
  Score, Ampel, Trend-Pfeil, 26-Wochen-Verlauf und einen Satz; oben Tacho, Ampelzone, Phase, 12-Monats-Verlauf.
- B2 (erledigt 17.09.2026) Profi-Ansicht mit Kennzahlen, Bestandteilen, Overlays, Erklaerungen, Rechenweg und
  Consensus-Verlauf seit 2009. Dazu der S&P-500-Vergleich (`frontend/src/components/dashboard/benchmark-panel.tsx`,
  Daten aus dem Backtest C1): was nach Wochen in jeder Ampelzone folgte (13 und 52 Wochen, Anteil positiver Faelle,
  Haeufigkeit der Zone) und wie sich zwei Regeln entlang der Zonen gegen schlichtes Halten geschlagen haetten
  (Rendite, Schwankung, groesster Rueckgang, Zeit im Markt). Bewusst ohne Quoten-Empfehlung, mit den Grenzen des
  Rueckblicks im Text.

Phase C: Backtest und Kalibrierung
- C1 (Engine erledigt 16.09.2026, backend/app/backtest.py, Endpunkt /api/v1/backtest, Rohbericht in
  docs/backtest-c1-raw.txt, Auswertung in docs/backtest-c1.md) Backtest-Engine: woechentlicher Consensus seit
  2009 gegen SPY (spaeter Bitcoin und Gold).
  Vorwaertsrenditen je Score-Band, Trefferquoten, Verhalten in 2008, 2020, 2022, einfache
  Regime-Strategie gegen Buy-and-Hold: Rendite, maximaler Drawdown, Sharpe, Zeit im Markt.
  Ergebnis: Rohwert komprimiert und schwach (IC13 +0,05), Rang ueber zehn Jahre deutlich besser (IC13 +0,17), deshalb
  Variante 1 (Rang plus Ampelzonen, drei Wochen Bestaetigung) umgesetzt (16.09.2026).
- C2 (erledigt 16.09.2026, `backend/app/calibrate.py`, Auswertung in docs/backtest-c2.md) Kalibrierung mit
  Walk-Forward: 2011 bis 2018 lernen, 2019 bis 2026 pruefen; Gitter ueber Treibergewichte, Mechanik-Vorzeichen,
  Bewertungs-Deckel, Vetos, Marktsignale invers, Liquiditaets-Momentum. Ergebnis: Gewichte 50/10/15/25
  (Liquiditaet/Marktsignale/Konjunktur/Struktur), Mechanik als Kontra (-5), Liquiditaets-Momentum 26 Wochen.
  Pruef-Fenster IC13 +0,35 statt +0,14. Nachtrag 16.09.2026: Marktsignale aus dem Score genommen und als Overlay
  Marktbestaetigung neu besetzt (docs/marktsignale-rolle.md); Kern 55/15/30, Pruef-Fenster IC13 +0,38.
- C3 (erledigt 16.09.2026, `backend/app/data_quality.py`, Endpunkt /api/v1/data-quality, Auswertung in
  docs/datenqualitaet-c3.md) Datenqualitaet: Pruefbericht ueber alle Serien; behoben: Look-ahead der Fed-Umfragen
  (30 Tage Verzug im Verlauf), Jahresrate bei fehlendem CPI-Monat, Verzug fuer MSPD und BoJ. Ohne Look-ahead sinkt
  IC13 auf +0,25 (ehrlich), Parameter bestaetigt. Dazu Zeithorizont-Umschalter (6 M bis Max) an allen Verlaufs-Charts.

Phase D: Betrieb
- D1 (erledigt 16.09.2026) Persistenz: SQLite unter backend/data (`app/store.py`) mit Rohdaten-Cache aller
  Quellen (20 h frisch, bei Netzausfall Rueckfall), Tagesbildern (`app/snapshots.py`) und Ereignissen. Taeglicher
  Refresh im Hintergrund der API (`app/refresh.py`, 07:30) oder per POST /api/v1/refresh; GET /api/v1/changes und
  /api/v1/snapshots.
- D2 (erledigt 16.09.2026, Konto-Schritte beim Nutzer, docs/hosting.md) Kostenloses Hosting als statischer Export:
  `python -m app.export` schreibt alle JSON-Dateien, `.github/workflows/daily.yml` laeuft taeglich in GitHub
  Actions und veroeffentlicht die statische Next.js-Seite auf GitHub Pages (Frontend-Modus
  NEXT_PUBLIC_DATA_MODE=static). Kein Backend online, keine Kaltstarts, keine Kosten. Vercel als Alternative.
- D3 (erledigt 16.09.2026) Hinweis bei Regimewechsel: `app/notify.py` meldet neue Ereignisse (Zone, Phase,
  Regime-Flags, Marktbestaetigung, Vetos) per ntfy.sh (kostenlos, ohne Konto) und/oder SMTP-E-Mail; im Dashboard
  die Liste "Was hat sich geaendert?" in beiden Modi.

## 5. Offene Punkte und Risiken

- FRED-Key ist hinterlegt. Der High-Yield-Spread (ICE BofA) ist auf FRED auch per API auf 3 Jahre
  begrenzt; fuer die Historie bleibt HYG/IEF der Kredit-Proxy, der Spread ergaenzt nur den Live-Wert.
- Shiller-Daten: Yale-Datei endet 2023, aktuelle Datei auf shillerdata.com, Parser mit Fallback multpl.
- Proprietaere Indikatoren (Global Liquidity Index, Dealer-Gamma, CTA-Exposure, BofA-Cashquote) sind
  bewusst durch freie Proxys ersetzt und im Tool so benannt.
- Backtest-Grenzen: Perzentile sind rollierend (kein Look-ahead), aber Datenrevisionen bei CPI und
  Umfragen lassen sich nicht rekonstruieren. Ergebnisse konservativ lesen.
- Rechtliches: Die Allokationstabelle des Dokuments wird nicht uebernommen. Das Tool zeigt Regime und
  Prinzip, keine Prozentquoten.
