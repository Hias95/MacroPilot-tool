# C3: Datenqualitaet (16.09.2026)

Werkzeug: `python -m app.data_quality` in `backend/` (Rohbericht `docs/datenqualitaet-c3-raw.txt`), als JSON unter
`/api/v1/data-quality`. Prueft je Rohserie und abgeleiteter Serie Umfang, Abstand, Luecken, Aktualitaet, Ausreisser
(robuste z-Werte der Veraenderungen, absolut bei Serien um null), Nullen und doppelte Termine; je Saeule die
Abdeckung auf dem Wochenraster und den Abgleich Live-Score gegen letzten Verlaufspunkt.

## Gefunden und behoben

1. **Look-ahead in der Konjunktur-Saeule.** Die regionalen Fed-Umfragen sind auf FRED zum Monatsanfang datiert,
   erscheinen aber ab Monatsmitte (New York), am dritten Donnerstag (Philadelphia) und am letzten Montag (Dallas).
   Im Verlauf war ein Monat damit bis zu vier Wochen zu frueh sichtbar. Jetzt gilt im Verlauf ein Verzug von 30
   Tagen (`PUBLICATION_LAG_DAYS["regional_fed"]`), live bleibt der juengste veroeffentlichte Monat.
2. **Jahresrate mit fehlendem Monat.** Der CPI fuer Oktober 2025 fehlt auf FRED (Regierungsstillstand). Die
   Jahresrate rechnete "zwoelf Beobachtungen zurueck" und verglich ab November 2025 mit dem falschen Vormonat.
   `services.year_over_year` sucht jetzt dieselbe Periode ein Jahr frueher nach Datum; ohne Vorjahreswert entfaellt
   der Punkt. Aendert den Struktur-Score um einen Punkt (44 auf 45).
3. **Kleiner Look-ahead bei Schuldenstand und BoJ-Bilanz.** Der T-Bill-Anteil (Treasury MSPD, Monatsende) erscheint
   am fuenften Geschaeftstag des Folgemonats, die BoJ-Bilanz (FRED JPNASSETS, zum Monatsanfang datiert) Anfang des
   Folgemonats. Im Verlauf jetzt 7 beziehungsweise 35 Tage Verzug; live unveraendert.
4. **Lange Rohwert-Historie.** Jede Saeule liefert jetzt bis zu 25 Jahre Rohwerte (monatlich 25 beziehungsweise 30
   Jahre), damit der Zeithorizont-Umschalter bis "Max" reicht.

## Geprueft und in Ordnung

- Wochenraster: alle sechs Saeulen 100 % Abdeckung ab ihrem Start, keine Luecke ueber die erlaubte Alterung hinaus.
- Live-Score gegen letzten Verlaufspunkt: identisch oder eine Woche neuer (Liquiditaet 55 gegen 54, Bewertung nutzt
  live den laufenden Shiller-Monat, im Verlauf erst den abgeschlossenen).
- Yahoo-Wochenbalken sind auf den Montag datiert und enthalten den Freitagsschluss; auf dem Sonntagsraster zaehlt
  nur die abgeschlossene Woche. FRED-Wochenreihen (WALCL, TGA am Mittwoch, Donnerstag veroeffentlicht) und EZB
  (Freitag, Dienstag veroeffentlicht, auf WALCL-Mittwoche ausgerichtet) sind am Sonntag publiziert.
- Ausreisser: alle gemeldeten sind echte Ereignisse (September/Oktober 2008, Maerz 2020, August 2011 bei TIPS,
  April 2025 beim VIX). Reverse Repo vor 2013 ist lueckenhaft und zaehlt als null, so wie dokumentiert.
- Veraltete Reihen: TDSP (Schuldendienst der Haushalte) kommt zwei Quartale nach Quartalsende, das ist normal und im
  Verzug von 170 Tagen abgebildet.

## Was das fuer den Backtest heisst

Ohne den Konjunktur-Look-ahead sinkt die Vorhersagekraft des Rangs ueber die gesamte Historie (2010 bis 2026)
von IC13 +0,30 auf +0,25 und IC26 von +0,35 auf +0,28 (`docs/backtest-c3-raw.txt`). Die defensive Strategie
verliert ihren Drawdown-Vorteil aus 2020 (-29,5 % statt -19,6 %), weil die Konjunkturwende jetzt erst mit der
Veroeffentlichung sichtbar wird. Das sind die ehrlichen Zahlen. Die Zonenleiter ist dafuer sauber monoton
(+1,8 / +3,4 / +3,6 / +4,1 / +10,6 % in 13 Wochen).

Die Kalibrierung wurde auf den korrigierten Daten wiederholt (`docs/kalibrierung-c3-raw.txt`): die aktuellen
Parameter (55/15/30, Liquiditaet 26 Wochen, Mechanik -5) liegen im Lernfenster bei +0,246 gegen +0,248 fuer das
Gitteroptimum, im Pruef-Fenster bei +0,395. Konjunktur ist mit 0,1 bis 0,2 weiterhin im Plateau, nur etwas
schwaecher als vorher. Keine Aenderung der Parameter.

## Bekannte Grenzen (nicht behebbar mit kostenlosen Quellen)

- **Revisionen.** FRED liefert die aktuelle Fassung, nicht den Stand von damals (kein ALFRED). Betroffen sind die
  Fed-Umfragen (Saisonfaktoren), CPI (Saisonfaktoren), TDSP, BIP und die Fed-Finanzierungsrechnung. Die Verlaeufe
  sind damit leicht "zu gut", vor allem bei Konjunktur und Bewertung/Buffett. Der Effekt ist klein gegen den
  Konjunktur-Look-ahead, aber nicht null.
- **Composite mit zwei von drei Regionen.** Live zaehlt ein Monat ab zwei Umfragen, im Verlauf steht der Endwert mit
  allen dreien. Kleiner Unterschied im laufenden Monat.
- **Shiller-Daten.** Der laufende Monat ist ein Teilmonat (Durchschnitt bis heute); live bewusst genutzt, im Verlauf
  ausgeschlossen.
