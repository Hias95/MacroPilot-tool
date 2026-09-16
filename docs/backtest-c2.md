# C2: Kalibrierung mit Walk-Forward (16.09.2026)

Rohdaten: `docs/backtest-c2-raw.txt` (Kalibrierung, 3619 Auswertungen), `docs/backtest-c2-backtest-raw.txt`
(Backtest nach der Kalibrierung, `/api/v1/backtest`). Skript: `python -m app.calibrate` in `backend/`.

## Aufbau

- Grundlage: der Consensus-Rang (Perzentil des Rohwerts ueber die vorherigen 520 Wochen, kein Blick in die Zukunft)
  gegen SPY-Vorwaertsrenditen ueber 4, 13, 26 und 52 Wochen. Cash zum 3-Monats-T-Bill.
- Walk-Forward: Rang-Wochen bis Ende 2018 zum Lernen (404 Wochen), ab 2019 zum Pruefen (402 Wochen). Nur das
  Lernfenster entscheidet, das Pruef-Fenster wird berichtet. Mehr Historie gibt es nicht: der Rohwert beginnt 2009,
  der Rang braucht zwei Jahre Vorlauf.
- Ziel: Mittel aus IC13 und IC26 (Spearman-Rangkorrelation) im Lernfenster.
- Stufe 1: alle Treibergewichte in 0,1-Schritten (286 Vektoren) x Liquiditaets-Momentum {13, 26, 52 Wochen} x
  Mechanik-Spanne {-5, 0, +5}. Stufe 2: 0,05-Schritte um die fuenf besten Vektoren x Bewertungs-Deckel an/aus x
  Vetos an/aus x Marktsignale normal/invers.

## Ergebnis

| Konfiguration | Lernen (IC13/26) | Pruefen (IC13/26) |
|---|---|---|
| Alt: 35/25/25/15, Liq 13 W, Mechanik +5 | +0,147 (0,13 / 0,17) | +0,155 (0,14 / 0,17) |
| Neu: 50/10/15/25, Liq 26 W, Mechanik -5 | +0,274 (0,20 / 0,35) | +0,361 (0,35 / 0,37) |
| Bestes Gitter: 60/0/20/20, Liq 26 W, Mechanik -5 | +0,298 (0,23 / 0,36) | +0,361 (0,35 / 0,37) |

Gewichte in der Reihenfolge Liquiditaet / Marktsignale / Konjunktur / Struktur & Fiskus.

Was die Randeffekte sagen (Mittel ueber alle anderen Kombinationen):

1. **Liquiditaet traegt.** Je hoeher ihr Gewicht, desto besser im Lern- und vor allem im Pruef-Fenster. 0,5 bis 0,7 ist
   das Plateau im Lernfenster.
2. **Marktsignale schaden als Treiber.** Jeder Zehntelpunkt Gewicht kostet IC, im Pruef-Fenster wird der IC ab 0,4
   negativ. Breite, Risikoappetit, Kupfer/Gold und Kredit laufen dem Markt nach, nicht voraus. Invers gerechnet
   bringen sie fast nichts (+0,01), das lohnt die Verwirrung nicht.
3. **Struktur & Fiskus verdient mehr Gewicht** (0,2 bis 0,4 gleich gut im Lernfenster, im Pruef-Fenster steigend),
   Konjunktur weniger (Optimum 0,2 bis 0,3 im Lernfenster, im Pruef-Fenster je weniger desto besser).
4. **Marktmechanik ist ein Kontra-Signal.** Spanne -5 (Stress hebt den Rohwert, Sorglosigkeit senkt ihn) schlaegt 0
   schlaegt +5, in beiden Fenstern.
5. **Liquiditaets-Momentum 26 Wochen** ist im Lernfenster klar besser als 13 (+0,28 vs +0,22 bei gleichen Gewichten),
   im Pruef-Fenster leicht schlechter (+0,33 vs +0,37). Bleibt bei 26, weil die Regel Lernfenster heisst, C1 dieselbe
   Richtung zeigte und der Score ruhiger wird (8,7 statt 11,4 Zonenwechsel pro Jahr ohne Hysterese).
6. **Bewertungs-Deckel und Vetos** aendern am IC nichts (sie greifen selten und dann am unteren Rand). Sie bleiben,
   weil sie die Fallhoehe und Systemkrisen abbilden, was der IC nicht misst.

## Entscheidung

Neue Parameter in `backend/app/model_config.py`: Gewichte Liquiditaet 0,50, Marktsignale 0,10, Konjunktur 0,15,
Struktur & Fiskus 0,25; `MECHANICS_RANGE = -5` (Kontra); Liquiditaets-Momentum 26 Wochen (T-Bill-Anteil 6 Monate).

Bewusst nicht das Gitteroptimum: Marktsignale behalten 0,10 statt 0. Mit 0 waere die Saeule nur noch Anzeige, das ist
eine Strukturfrage (vier Treiber oder drei Treiber plus Marktbestaetigung), keine Kalibrierfrage. Kosten der Wahl:
etwa 0,02 IC im Lernfenster, im Pruef-Fenster keine. **Offen fuer den Nutzer:** Marktsignale zur Bestaetigung
degradieren (Gewicht 0, eigene Zeile "Was der Markt gerade tut", Divergenz-Hinweis) oder als kleiner Treiber lassen.

## Backtest nach C2 (gesamte Historie 2011 bis 2026, `docs/backtest-c2-backtest-raw.txt`)

Vorsicht: 2011 bis 2018 ist Lernfenster, die ehrlichen Zahlen stehen in der Tabelle oben (Pruefen).

| | vor C2 (C1-Rang) | nach C2 |
|---|---|---|
| IC 13 W / 26 W / 52 W | +0,17 / +0,19 / +0,15 | +0,30 / +0,35 / +0,23 |
| 13-W-Rendite je Zone (Stark negativ bis Stark positiv) | +3,0 / +1,6 / +3,0 / +4,5 / +6,0 % | +2,5 / +1,7 / +3,6 / +4,6 / +9,2 % |
| Trefferquote Stark positiv | 93 % | 100 % (8,6 % der Wochen) |
| Strategie Basis (50/70/85/100/100) | CAGR 13,0 %, DD -21 % | CAGR 13,2 %, Sharpe 0,90, DD -29 % |
| Strategie defensiv (0/25/50/75/100) | Sharpe 1,16, DD -9 % | CAGR 10,3 %, Sharpe 0,99, DD -19,6 % |
| Buy and Hold | CAGR 13,9 %, Sharpe 0,79, DD -32 % | gleich |
| Zonenwechsel pro Jahr mit 3-Wochen-Bestaetigung | 4,7 | 3,8 |

Lesart: Der Rang trennt jetzt deutlich (Dezile 13 W von +2,4 % unten bis +8,5 % oben), Stark positiv ist die
verlaesslichste Zone. Stark negativ liegt ueber Negativ, das ist der Kontra-Effekt aus Mechanik und Panik-Zone:
extreme Angst war Wendepunkt. Die defensive Strategie hat nach C2 einen tieferen Drawdown als in C1 (-19,6 % statt
-9 %), weil der Rang 2020 und 2022 spaeter aus dem Markt ging als der geglaettete C1-Rang; dafuer sind Rendite
und Trefferquoten hoeher. Kein Modell schlaegt Buy and Hold in der Rendite, das Ziel ist ein besseres Verhaeltnis
von Rendite zu Drawdown, und das liefert es (Sharpe 0,90 bis 0,99 gegen 0,79).

## Grenzen

- 15 Jahre Historie, ein Bullenmarkt mit zwei kurzen Crashs. Die Pruef-Zahlen sind ermutigend, aber kein Beweis.
- Vorwaertsrenditen ueberlappen, die effektive Stichprobe ist klein. Unterschiede unter 0,03 IC sind Rauschen.
- Der Rang vergleicht mit den zehn Jahren davor, also mit dem Regime der Zeit. In einem Regimewechsel (etwa dauerhaft
  hohe Inflation) braucht er Zeit.
