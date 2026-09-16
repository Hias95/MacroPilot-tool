# Backtest C1: Consensus gegen S&P 500 (SPY), 2009 bis 2026

Stand 16.09.2026. Engine: backend/app/backtest.py, Endpunkt /api/v1/backtest, Rohdaten in backtest-c1-raw.txt.
Methode: Score vom Sonntag, Rendite ab der Folgewoche (kein Blick in die Zukunft). Rangkorrelation (IC) =
Spearman zwischen Score und Vorwaertsrendite. Strategie = Aktienquote je Zone (0/25/50/75/100 %), Rest T-Bill.
Grenzen: eine Periode (ein langer Bullenmarkt mit zwei Crashs), keine Datenrevisionen rekonstruierbar,
alle Parameter in-sample. Ergebnisse sind Richtungsaussagen, keine Garantien.

## 1. Der aktuelle Consensus v2 ist zu komprimiert und schwach

| Variante | Verteilung (p10 / Median / p90) | IC 13W | IC 52W | Sharpe | Max. Drawdown | CAGR (B&H 15,3 %) |
|---|---|---|---|---|---|---|
| v2 roh | 39 / 53 / 69 | +0,05 | -0,02 | 0,95 | -13,8 % | 9,4 % |
| v2 geglaettet 4W | 39 / 52 / 68 | +0,04 | -0,04 | 0,98 | -13,6 % | 9,6 % |
| Ungewichtetes Mittel, ohne Overlays | 39 / 52 / 68 | +0,07 | -0,03 | 0,98 | -11,6 % | 9,5 % |
| Stimmen-Modell (4 Treiber) | 25 / 58 / 93 | +0,09 | +0,01 | 1,07 | -17,1 % | 12,2 % |
| Rang, wachsendes Fenster | 6 / 38 / 81 | +0,11 | +0,08 | 1,14 | -9,4 % | 9,0 % |
| **Rang, rollierend 10 Jahre** | 7 / 39 / 82 | **+0,17** | **+0,14** | **1,16** | **-9,2 %** | 9,3 % |

Befund: Das gewichtete Mittel von vier Perzentil-Scores staucht die Verteilung (Standardabweichung 11 statt
29 bei einer Gleichverteilung). Die Zonen Sturm und Volle Fahrt werden deshalb praktisch nie erreicht. Das ist
Mathematik, keine Glaettung: die 4-Wochen-Glaettung aendert die Streuung kaum (10,8 statt 11,3), halbiert aber
die Zonenwechsel (3,8 statt 7,4 pro Jahr).

Die Rangnormierung des Consensus ueber ein rollierendes Zehn-Jahres-Fenster loest beides: Die Zonen sind per
Konstruktion besetzt (Sturm 27 %, Gegenwind 22 %, Wechselhaft 25 %, Rueckenwind 14 %, Volle Fahrt 12 %),
und die Vorwaertsrenditen werden monoton: 13 Wochen nach "Sturm" +3,0 % (68 % Treffer), nach "Volle Fahrt"
+6,0 % (93 % Treffer). Die Rangkorrelation steigt von +0,05 auf +0,17.

## 2. Zonenwechsel: Bestaetigungsfrist statt Glaettung

| Variante | ohne | 2 Wochen | 3 Wochen | 4 Wochen | 6 Wochen |
|---|---|---|---|---|---|
| v2 roh | 7,4 / Jahr | 4,7 | 3,3 | 2,7 | 1,5 |
| Rang rollierend | 15,4 / Jahr | 7,9 | 5,2 | 3,6 | 1,7 |

Empfehlung: Zahl roh zeigen, nur das Label mit dreiwoechiger Bestaetigung wechseln (etwa 5 Wechsel pro Jahr).

## 3. Was die Strategie fuer Privatanleger leistet

Mit der Standard-Quote (0/25/50/75/100 %) halbiert der Rang-Consensus den maximalen Drawdown (-9 % statt -32 %),
kostet aber in einem Bullenmarkt rund 4,5 Punkte Rendite pro Jahr, weil die Quote im Schnitt nur 41 % betraegt.
Mit einer hoeheren Basisquote (50/70/85/100/100 %) liefert derselbe Consensus 13,0 % pro Jahr gegen 13,9 % fuer
Kaufen-und-Halten, bei einem Drawdown von -21 % statt -32 % und 2022 mit -14 % statt -18 %. Das ist das
praktische Versprechen: fast die volle Rendite, ein Drittel weniger Absturz.

## 4. Die Saeulen einzeln: Ergebnisse fuer die Kalibrierung (C2)

| Saeule | IC 13W | IC 26W | IC 52W | Lesart |
|---|---|---|---|---|
| Struktur & Fiskus | +0,15 | +0,19 | +0,11 | staerkster Kurzfrist-Praediktor |
| Bewertung | +0,10 | +0,10 | +0,23 | wirkt auf 12 Monate, wie erwartet |
| Liquiditaet | +0,02 | +0,05 | +0,10 | wirkt erst auf 12 Monate; 13-Wochen-Momentum zu kurz |
| Konjunktur | +0,03 | +0,01 | -0,05 | gleichlaufend, kaum Vorlauf |
| Marktsignale | -0,04 | -0,02 | -0,13 | kontraer: schwache Marktsignale gehen starken Renditen voraus |
| Marktmechanik | -0,21 | -0,19 | -0,10 | stark kontraer: hoher VIX = hohe Folgerendite |

Konsequenzen fuer C2: Struktur hoeher gewichten, Liquiditaet mit laengerem Momentum (26 bis 52 Wochen)
rechnen, Konjunktur pruefen, Marktsignale und Mechanik nicht linear addieren, sondern als Kontra-Signal an
Extremen und als Drawdown-Warnung nutzen. Die Mechanik-Korrektur von plus/minus 5 Punkten hat fuer die
erwartete Rendite das falsche Vorzeichen.

## 5. Empfehlung fuer die Darstellung (Entscheidung offen)

Rang 1: Rang-Skala. Consensus als Perzentil der letzten zehn Jahre, fuenf Zonen als Quantile (10/30/70/90),
Label wechselt erst nach drei Wochen, Zahl bleibt roh. Rang 2: Stimmen-Modell ("3 von 4 Treibern dafuer") als
Label, Zahl daneben. Rang 3: Absolute Zonen mit kalibrierten Schwellen (aktuell 39/47/60/69).
