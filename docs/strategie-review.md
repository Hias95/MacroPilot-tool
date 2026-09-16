# MacroPilot: Strategie-Review

Stand: 15.09.2026. Ergebnis der Pruefung von Vision, Logik und Tech-Stack vor dem MVP-Start.
Kurzfassung: Die Idee ist stark, aber drei Annahmen im Plan sind in der Praxis falsch oder
unvollstaendig. Wer sie frueh korrigiert, spart spaeter einen Umbau.

## 1. Trend schlaegt Niveau (wichtigste Korrektur)

Alle vier Saeulen muessen die **Veraenderung** messen, nicht den absoluten Stand.

- Die Fed-Bilanz schrumpft seit 2022, trotzdem lief der Markt. Der absolute WALCL-Wert sagt fast nichts.
  Der 13- oder 26-Wochen-Trend sagt viel.
- Eine Inflation von 3 % ist bullisch, wenn sie faellt, und baerisch, wenn sie steigt.
- Ein ISM von 48 ist ein Kaufsignal, wenn er von 45 kommt, und ein Warnsignal, wenn er von 52 kommt.

Empfehlung: Jede Saeule bekommt zwei Komponenten, **Niveau** (Perzentil-Rang ueber 10 Jahre) und
**Momentum** (Richtung ueber 3 Monate). Der Score ist eine Mischung, z. B. 40 % Niveau, 60 % Momentum.
Perzentil-Rang ist fuer Hobby-Investoren erklaerbar: "Liquiditaet ist besser als in 80 % der letzten 10 Jahre."

## 2. WALCL ist nicht Net Liquidity

Howells Proxy fuer US-Liquiditaet ist **Net Liquidity = WALCL minus TGA minus Reverse Repo**.
Alle drei Serien liegen auf FRED:

| Serie        | FRED-ID     | Frequenz  |
|--------------|-------------|-----------|
| Fed-Bilanz   | WALCL       | woechentlich |
| TGA          | WTREGEN     | woechentlich |
| Reverse Repo | RRPONTSYD   | taeglich  |

Schritt 2 sollte diese Formel im Backend berechnen. Langfristig zaehlt fuer einen deutschen Investor
die **globale** Liquiditaet: EZB (FRED: ECBASSETSW), BoJ und PBoC, umgerechnet in USD.

## 3. ISM PMI liegt NICHT auf FRED (groesste Luecke im Plan)

ISM hat die Lizenz fuer FRED 2016 zurueckgezogen. Der Plan "ISM ueber FRED" scheitert.

Optionen:
- **Regional-Fed-Composite** als Proxy: Durchschnitt aus Philly (GACDFSA), New York, Richmond, Dallas,
  Kansas City. Alle auf FRED, tracken den ISM historisch eng. Empfehlung fuer den Start.
- ISM-Headline manuell monatlich eintragen (ismworld.org veroeffentlicht die Zahl oeffentlich).
- S&P Global PMI: kostenpflichtig.
- Alternativ CFNAI (Chicago Fed National Activity Index), breiter, aber traeger.

## 4. Druckenmiller-Saeule ist als geplant zu datenhungrig

"Prozent der S&P-500-Aktien ueber 200-Tage-Linie" braucht 500 Ticker taeglich ueber yfinance.
Das ist langsam, bricht oft und wird von Yahoo gedrosselt.

Bessere Proxies, jeweils nur zwei Ticker:

| Frage                    | Ratio       | Lesart                                   |
|--------------------------|-------------|------------------------------------------|
| Marktbreite              | RSP / SPY   | Gleichgewicht schlaegt Cap-Weight = breit |
| Risikoappetit            | XLY / XLP   | Zykliker vor Defensiven = Risk-On        |
| Wachstums-Fuehrung       | SMH / SPY   | Halbleiter fuehren = Zyklus dreht auf    |
| Kredit-Stress            | HYG / IEF   | High Yield vor Treasuries = entspannt    |
| Realwirtschaft           | Kupfer/Gold | Kupfer vorne = Wachstum                  |

Kredit-Spreads gibt es zusaetzlich direkt auf FRED (BAMLH0A0HYM2).

## 5. Consensus ist kein Durchschnitt

Die vier Saeulen laufen auf verschiedenen Zeithorizonten. Liquiditaet fuehrt um 6 bis 12 Monate,
der PMI ist etwa gleichlaufend, Marktbreite reagiert in Wochen, Inflation und Zinskurve in Quartalen.
Ein Mittelwert verwischt genau die Information, die den Nutzer interessiert.

Vorschlag fuer die Jahreszeiten-Logik:

1. **Jahreszeit** aus einer 2x2-Matrix: Liquiditaets-Trend (steigt/faellt) mal Wachstums-Trend (steigt/faellt).
   Das ist die klassische Investment-Clock-Logik.
   - Liquiditaet rauf, Wachstum rauf: Sommer
   - Liquiditaet rauf, Wachstum runter: Fruehling (Erholung wird vorbereitet)
   - Liquiditaet runter, Wachstum rauf: Herbst (Spaetzyklus)
   - Liquiditaet runter, Wachstum runter: Winter
2. **Dalio** ist ein Risiko-Overlay: hohe Inflation plus inverse Kurve deckelt den Score nach oben.
3. **Druckenmiller** ist die Bestaetigung: widerspricht der Markt der Makro-Story, wird der Score
   Richtung 50 gezogen (Unsicherheit), bestaetigt er sie, wird er verstaerkt.

Der Tacho bleibt als Zusammenfassung, die Jahreszeit wird der Held. Dazu ein Satz "Warum":
"Fruehling, weil die Fed-Bilanz seit 13 Wochen waechst und der PMI von 47 auf 49,8 gedreht hat."

## 6. Vertrauen durch Historie

Hobby-Investoren glauben einem Score erst, wenn sie sehen, was er 2008, 2020 und 2022 gesagt haette.
Deshalb: Zeitreihen ab Tag 1 speichern, nicht nur den letzten Wert. Spaeter ein Chart
"Consensus Score vs. S&P 500 seit 2005". Das ist zugleich das Werkzeug, um Schwellen zu kalibrieren.

Architektur dafuer: taeglicher Job (GitHub Actions, Supabase pg_cron oder ein Scheduler im Backend)
holt die Daten und schreibt sie in Supabase. Das Frontend liest aus der Datenbank, nie live von FRED.

## 7. Datenfrische sichtbar machen

Makro-Daten hinken. WALCL ist mittwochs datiert und donnerstags veroeffentlicht, CPI kommt monatlich
mit zwei Wochen Verzug. Jede Kachel zeigt deshalb "Stand: Datum" und die Frequenz. Ist im MVP umgesetzt.

## 8. Tech-Stack: Bewertung

- **FastAPI** ist gerechtfertigt: pandas/numpy fuer Perzentile und Rolling Windows, yfinance ist Python.
  Preis: zwei Deployments (Vercel fuer das Frontend, Railway/Fly/Render fuer das Backend).
- **Supabase** braucht das MVP noch nicht. Auth erst, wenn es Watchlists oder Alerts gibt.
- **FRED ohne Key** funktioniert ueber den CSV-Export, fuer Produktion aber den kostenlosen Key setzen.
- **Caching** ist Pflicht. FRED erlaubt 120 Anfragen pro Minute, und WALCL aendert sich einmal pro Woche.

## 8b. Kosten: Das Tool laeuft ohne laufende Kosten

- Datenquellen: FRED ist kostenlos (Key optional), Marktdaten ueber yfinance sind kostenlos.
- Erklaerungen: regelbasiert (immer), lokal ueber Ollama (kostenlos, eigene GPU) oder ueber Gemini
  (Gratis-Kontingent, nur Eigengebrauch im EWR). Claude-API nur, wenn man bewusst zahlen will.
- Abos (Claude Pro, Gemini Pro) enthalten keinen API-Zugang fuer eigene Apps.
- Hosting spaeter: Vercel Hobby (Frontend), ein kostenloser Backend-Host (Render Free, Hugging Face Spaces)
  und Supabase Free. Alternativ die Python-Logik in Next.js-API-Routen ueberfuehren, dann reicht Vercel allein.

## 9. Rechtliches und Tonalitaet

Das Tool beschreibt Regime, es gibt keine Handlungsempfehlungen. Kein "Kaufen", kein "Verkaufen",
sondern "Fruehling: Erholung setzt ein". Ein sichtbarer Disclaimer ("keine Anlageberatung") gehoert auf
jede Seite. Fuer Deutschland ist das die saubere Grenze zur Anlageberatung nach WpHG.

## 10. Score-Semantik (festgelegt)

- 0 = maximal Risk-Off (Winter), 100 = maximal Risk-On (Sommer).
- Farbverlauf rot, bernstein, gruen. Ueberall gleich, auch in den Kacheln.
- Jede Saeule hat Persona ("Der Klempner") und Kachel-Titel ("Die Geld-Flut"). Beides wird immer zusammen gezeigt.

## Roadmap-Vorschlag

| Schritt | Inhalt                                                                 |
|---------|------------------------------------------------------------------------|
| 1       | Dashboard-UI, WALCL live in Kachel 1 (erledigt)                        |
| 2       | Net Liquidity (WALCL - TGA - RRP), Perzentil- und Momentum-Score im Backend (erledigt) |
| 3       | Saeule 2: Regional-Fed-Composite als PMI-Proxy (erledigt; Richmond und Kansas City fehlen auf FRED, daher Philadelphia, New York, Dallas) |
| 4       | Saeule 3: ETF-Ratios RSP/SPY, XLY/XLP, SMH/SPY, HYG/IEF ueber den Yahoo-Chart-Endpunkt (erledigt) |
| 5       | Saeule 4: T10Y2Y, CPILFESL, DFII10 (Realzins) (erledigt)                |
| 6       | Consensus nach Jahreszeiten-Logik mit "Warum"-Satz (erledigt); Historien-Chart offen |
| 7       | Supabase-Persistenz, taeglicher Fetch-Job, Deployment                   |
| 8       | Auth, Watchlist, E-Mail-Alert bei Jahreszeiten-Wechsel                  |
