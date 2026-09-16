# MacroPilot

Makro-Daten (Liquiditaet, Konjunktur, Struktur & Fiskus als Treiber; Bewertung, Marktmechanik, Marktsignale als Overlays) als simples Ampel-Dashboard.
Design-Motto: Bloomberg Terminal trifft Apple. Stand: Modell v2 (drei Treiber, drei Overlays), Easy- und Profi-Modus,
Backtest C1, Kalibrierung C2. Der Consensus wird als Rang gezeigt ("besser als X % der Wochen der letzten zehn Jahre") mit Ampelzone und
Zyklusphase, die Begruendung ist regelbasiert. Jede Saeule bekommt eine KI-Erklaerung (Ollama lokal, optional Gemini
oder Anthropic).

## Struktur

```
frontend/   Next.js 16 (App Router), Tailwind 4, shadcn/ui, Recharts
backend/    FastAPI, FRED-Client, In-Memory-Cache
docs/       Strategie-Review und Roadmap
```

## Starten

Backend (Terminal 1):

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend (Terminal 2):

```bash
cd frontend
npm run dev
```

Dashboard: http://localhost:3000 - API-Doku: http://localhost:8000/docs

## FRED API-Key (optional, empfohlen)

Kostenlos unter https://fred.stlouisfed.org/docs/api/api_key.html. Dann in `backend/.env` eintragen
(Vorlage: `backend/.env.example`). Ohne Key nutzt das Backend den keylosen CSV-Export von FRED.

## Easy- und Profi-Modus

Der Umschalter im Header (gemerkt im Browser) waehlt die Ansicht. Einfach: Gesamtrang mit Ampelzone, Zyklusphase und
Verlauf, dazu je Baustein nur Score, Ampel, Trend-Pfeil (Score-Veraenderung ueber vier Wochen), Score-Verlauf
und ein Satz ohne Zahlen (`backend/app/easy.py`, Felder `easy_label` und `easy_summary`). Profi: alle Kennzahlen,
Bestandteile, Teil-Scores, Rechenweg, Regime-Checks und Erklaerungen. Jeder Verlaufs-Chart hat einen Umschalter
fuer den Zeithorizont (6 M, 1 J, 3 J, 5 J, 10 J, Max; `frontend/src/lib/range.ts`, je Chart im Browser gemerkt).
Datenqualitaet: `docs/datenqualitaet-c3.md` (Verzuege, Luecken, Grenzen der kostenlosen Quellen).

## Betrieb (Phase D)

Persistenz: `backend/data/macropilot.sqlite` (`app/store.py`) haelt die Rohdaten aller Quellen (Neustart ohne Netz,
Rueckfall bei Ausfall), ein Tagesbild des Dashboards je Tag und die erkannten Wechsel. Der Refresh laeuft taeglich
um 07:30 im Hintergrund der API (`AUTO_REFRESH`, `REFRESH_HOUR`) oder per `POST /api/v1/refresh`. Hinweise bei
Regimewechsel per ntfy.sh oder E-Mail (`NTFY_TOPIC`, `SMTP_*` in `backend/.env`), im Dashboard als Liste "Was hat
sich geaendert?". Hosting ohne Kosten als statischer Export auf GitHub Pages: `docs/hosting.md`
(`python -m app.export`, `.github/workflows/daily.yml`, Frontend mit `NEXT_PUBLIC_DATA_MODE=static`).

## Erklaerungen: kostenlos oder mit KI

Jede Saeule bekommt einen Text "Warum dieser Score?". Das Backend waehlt den Provider automatisch
(`EXPLAIN_PROVIDER=auto`), erzwingen geht ueber `backend/.env`:

| Provider   | Kosten                          | Einrichtung                                                              |
|------------|---------------------------------|--------------------------------------------------------------------------|
| template   | keine, laeuft immer             | nichts. Regelbasierter Text aus den Zahlen, Standard ohne Keys           |
| ollama     | keine, lokales Modell           | https://ollama.com/download installieren, `ollama pull gemma3:12b`      |
| gemini     | Gratis-Kontingent, Limits       | Key unter https://aistudio.google.com/apikey, als `GEMINI_API_KEY` setzen |
| anthropic  | pay-as-you-go                   | Key unter https://console.anthropic.com/settings/keys                    |

Hinweise: Ein Claude-Pro- oder Gemini-Abo deckt keine API-Aufrufe aus eigenen Apps ab, das sind getrennte
Produkte. Googles Gratis-Kontingent darf laut Google-Bedingungen im EWR, in UK und der Schweiz nur fuer den
Eigengebrauch genutzt werden, nicht um die App anderen anzubieten. Faellt ein KI-Provider aus, springt der
regelbasierte Text ein und zeigt den Grund an. Texte werden pro Datenstand gecacht.

## Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest
```

## Endpunkte

| Methode | Pfad                                    | Inhalt                                                     |
|---------|-----------------------------------------|------------------------------------------------------------|
| GET     | /health                                 | Status, ob FRED- und Anthropic-Key gesetzt sind            |
| GET     | /api/v1/dashboard                       | Alle vier Saeulen plus Consensus (ein Request fuer die UI) |
| GET     | /api/v1/pillars/{id}                    | Eine Saeule: liquidity, cycle, markets, structure          |
| GET     | /api/v1/pillars/{id}/explanation        | KI-Erklaerung zum aktuellen Score (gecacht pro Datenstand) |
| GET     | /api/v1/backtest                        | Backtest des Consensus gegen SPY: Zonen, Rangkorrelation, Strategie (C1, Auswertung nach C2 in docs/backtest-c2.md) |
| GET     | /api/v1/history?years=N                 | Score-Verlauf aller Saeulen und des Consensus, woechentlich seit 2003 |
| GET     | /api/v1/data-quality                    | Datenqualitaet: Luecken, Aktualitaet, Ausreisser, Rasterabdeckung, Live gegen Verlauf (C3) |
| POST    | /api/v1/refresh                         | Quellen neu laden, Tagesbild speichern, Wechsel melden (Header X-Refresh-Token, wenn gesetzt) |
| GET     | /api/v1/changes?days=N                  | Erkannte Wechsel (Zone, Phase, Regime, Marktbestaetigung, Vetos) |
| GET     | /api/v1/snapshots?days=N                | Tagesbilder des Dashboards (Point-in-time) |
| GET     | /api/v1/liquidity/fed-balance-sheet     | Rohserie WALCL (Schritt 1, bleibt fuer Debugging)          |

## Score-Logik

Saeule 1 (Liquiditaet): drei gewichtete Signale. Net Liquidity = WALCL - WTREGEN - RRPONTSYD (50 %),
Notenbank-Proxy Fed + EZB (ECBASSETSW) + BoJ (JPNASSETS) in USD ueber die Wochenkurse EURUSD und USDJPY (30 %,
Ersatz fuer Howells proprietaeren Global Liquidity Index) und der T-Bill-Anteil an den marktfaehigen
Staatsschulden aus der Treasury-API (20 %, Fiskal-Impuls). Score je Signal = 40 % Niveau + 60 % Momentum,
Niveau = Perzentil ueber 10 Jahre, Momentum = Perzentil der 13-Wochen-Veraenderung. Vor 2013 zaehlt fehlendes
Reverse Repo als null.

Saeule 2 (Konjunktur): ISM liegt nicht auf FRED. Ersatz ist der monatliche Durchschnitt der regionalen
Fed-Industrieumfragen GACDFSA066MSFRBPHI (Philadelphia), GACDISA066MSFRBNY (New York) und BACTSAMFRBDAL
(Dallas). Ein Monat zaehlt, sobald mindestens zwei Regionen gemeldet haben. Score wie oben, nur mit
3-Monats-Momentum und 120 Monaten Historie.

Saeule 3 (Marktsignale): vier Wochenkurs-Signale vom Yahoo-Chart-Endpunkt: RSP/SPY (Breite), AUD/JPY
(Risikoappetit), Kupfer/Gold aus den Futures HG=F und GC=F (Realwirtschaft) und HYG/IEF (Kredit, Proxy fuer
den High-Yield-Spread, dessen FRED-Historie auf drei Jahre begrenzt ist). Jedes Signal bekommt einen eigenen
Score, der Saeulen-Score ist ihr Mittel. Niveau-Fenster 5 Jahre, weil Verhaeltnisse wie RSP/SPY jahrzehntelange
Trends haben. yfinance wurde bewusst nicht eingebunden (pandas, curl_cffi, Zertifikatsproblem auf diesem Rechner).

Saeule 4 (Struktur & Fiskus): fuenf gewichtete Bestandteile: Zinskurve T10Y2Y (30 %) mit Un-Inversions-Regel
(Versteilung nach Inversion deckelt den Kurven-Score), Realzins DFII10 (25 %, invertiert), Kerninflation CPILFESL
(15 %, invertiert), Schuldendienstquote TDSP (15 %, invertiert), Zinslast des Bundes zu Steuereinnahmen
A091RC1Q027SBEA / W006RC1Q027SBEA (15 %, invertiert). Quartals- und Monatsdaten werden in der Historie um ihren
Veroeffentlichungsverzug verschoben (kein Look-ahead). Dazu das Regime-Flag "Fiskalische Dominanz": aktiv,
wenn zwei von drei zutreffen: Zinslast ueber 25 %, T-Bill-Anteil ueber 20 % (Treasury Fiscal Data API,
`backend/app/treasury.py`), Realzins-Repression unter null.

Overlay Marktmechanik (`backend/app/pillars/mechanics.py`): VIX-Niveau (40 %), Terminstruktur VIX/VIX3M (40 %)
und SKEW (20 %), alle invertiert. VIX und VIX3M kommen als CSV vom CBOE-CDN (`backend/app/cboe.py`), SKEW von
Yahoo. Ersatz fuer die proprietaeren Gamma-, CTA- und Cashquoten-Daten. Panik-Regel: VIX im obersten Zehntel
der letzten zehn Jahre = "Panik-Zone" (historisch eher Kaufzone). Overlays fliessen nicht in die Jahreszeit
ein, sondern als Deckel und Warnung in den Consensus (Schritt A7). API: `overlays` im Dashboard.

Overlay Bewertung (`backend/app/pillars/valuation.py`): Shiller CAPE (40 %, invertiert), Excess CAPE Yield als
Risikopraemie (40 %) und Buffett-Indikator NCBEILQ027S / GDP (20 %, invertiert). 80 % Niveau ueber 30 Jahre, weil
Bewertung Fallhoehe misst, nicht Timing. Shiller-Daten kommen von shillerdata.com (`backend/app/shiller.py`,
Link wird von der Seite gelesen, Fallback Yale-Datei). Regime-Flag "Extreme Bewertung": zwei von drei: CAPE im
obersten Zehntel, Praemie unter 1 %, Buffett im obersten Zehntel. Ausgabe: Fallhoehe-Label guenstig/fair/teuer/extrem.

Consensus v2 (`backend/app/consensus.py`, Parameter in `model_config.py`): Kern = gewichtetes Mittel der drei
Treiber (nach Kalibrierung C2: Liquiditaet 55 %, Konjunktur 15 %, Struktur & Fiskus 30 %). Marktsignale sind seit
dem 16.09.2026 kein Treiber mehr, sondern das Overlay Marktbestaetigung (`docs/marktsignale-rolle.md`): Badge
"Markt bestaetigt / zoegert / laeuft voraus" gegen den Rang, Regime-Flag Marktstress (Score unter 30) und
Kapitulation (unter 20).
Marktmechanik korrigiert um bis zu 5 Punkte als Kontra-Signal: Stress hebt den Rohwert, Sorglosigkeit senkt ihn
(extreme Angst war historisch eher Kaufzone). Bewertung deckelt nach oben: Deckel =
60 + 0,4 x Bewertungs-Score. Vetos: Liquiditaet unter 20 deckelt bei 35, Struktur unter 20 bei 30, extreme Bewertung
plus gestresste Markttechnik bei 40. Dieser Rohwert ist komprimiert (Backtest C1), deshalb zeigt das Tool seinen Rang
gegenueber den letzten zehn Jahren (`RANK_WINDOW_WEEKS`): "besser als X % der Wochen". Die Ampelzone ist das Quantil des
Rangs (unter 10 Stark negativ, 10 bis 30 Negativ, 30 bis 70 Neutral, 70 bis 90 Positiv, ab 90 Stark positiv) und wechselt
erst nach drei Wochen in Folge (`ZONE_CONFIRM_WEEKS`); die Zahl selbst bleibt ungeglaettet. Die Zyklusphase (Erholung,
Aufschwung, Spaetzyklus, Abschwung) kommt aus Richtung Liquiditaet x Richtung Konjunktur und wechselt erst nach vier
Wochen Bestaetigung. Die Begruendung ist regelbasiert.

