# Muss es ein Liquiditätsmodell sein? Was die Daten sagen

Stand: 18.09.2026. Anlass: Das Modell-Panel weist aus, dass Net Liquidity allein 27,5 Prozent und die
Notenbankbilanzen zusammen 44 Prozent des Gesamtscores bestimmen. Die Frage dazu: Ist das sachlich richtig,
oder gibt es Lagen, in denen andere Kräfte den Markt stärker treiben, und lässt sich daraus eine Regel bauen?

Untersucht mit `python -m app.research_regimes`, Rohbericht in `docs/regime-analyse-raw.txt`. Gemessen wird
die Rangkorrelation zwischen dem Score eines Bausteins und der Rendite des S&P 500 in den folgenden 13 bzw.
26 Wochen, 2008 bis 2026, 952 Wochen. Neben jeder Zahl steht die Zahl echt überschneidungsfreier Fenster,
weil wöchentliche Messungen über 13 Wochen einander zu zwölf Dreizehnteln überlappen.

## 1. Die kurze Antwort

**Nein, die 55 Prozent sind durch die Daten nicht gedeckt.** Über den ganzen Zeitraum ist Struktur & Fiskus
mindestens so aussagekräftig wie die Liquidität, auf beiden Horizonten.

**Ja, es ist situationsabhängig. Nein, wir können das nicht sauber ausnutzen.** Fast jeder Umfeld-Befund
dreht das Vorzeichen, sobald man ihn getrennt in den beiden Hälften des Zeitraums prüft. Was wie ein Regime
aussieht, ist überwiegend ein Zeitraum-Effekt.

**Der wichtigste Befund steht quer zu allem anderen:** Die Prognosekraft des gesamten Modells ist ein
Phänomen der Jahre ab 2018. Davor lag sie bei praktisch null.

## 2. Einzelne Bausteine, ganzer Zeitraum

Rangkorrelation zur Rendite der folgenden 13 Wochen, 952 Wochen, 74 unabhängige Fenster:

| Baustein | 13 Wochen | 26 Wochen |
|---|---|---|
| Struktur & Fiskus | +0,15 | +0,19 |
| Liquidität | +0,10 | +0,16 |
| Bewertung | +0,10 | +0,11 |
| Konjunktur | +0,03 | −0,06 |
| Marktsignale | −0,04 | −0,02 |
| Marktmechanik | **−0,21** | −0,19 |

Die Rangfolge widerspricht der Gewichtung. Der Baustein mit dem größten Gewicht ist nicht der
aussagekräftigste, und die Konjunktur mit 15 Prozent liefert für sich genommen nichts.

## 3. Umfeld-Abhängigkeit: der verführerische Befund

Teilt man nach wirtschaftlich begründeten Umfeldern, sieht es nach klaren Regeln aus:

| Umfeld | Fenster | Liquidität | Struktur |
|---|---|---|---|
| Realzins negativ | 20 | **+0,51** | +0,42 |
| Realzins über 1 % | 29 | −0,07 | +0,04 |
| Kerninflation über 3 % | 18 | +0,24 | +0,25 |
| Kerninflation 2 bis 3 % | 29 | −0,06 | −0,04 |
| Bewertung extrem teuer | 14 | +0,40 | +0,28 |
| Konjunktur stark | 25 | +0,36 | +0,28 |

Die naheliegende Regel wäre: Bei negativem Realzins zählt die Liquidität stark, bei teurem Geld kaum. Genau
das würde ich ohne weitere Prüfung auch glauben, denn es klingt ökonomisch plausibel: Ist Geld real gratis,
wandert zusätzliche Liquidität in Vermögenswerte; kostet Geld real etwas, konkurriert der sichere Zins.

## 4. Warum die Regel trotzdem nicht ins Tool gehört

Dieselben Umfelder, getrennt nach Zeitraum gerechnet:

| Umfeld | Liquidität bis 2017 | Liquidität ab 2018 |
|---|---|---|
| Alle Wochen | **−0,15** | **+0,33** |
| Realzins negativ | +0,31 | +0,71 |
| Realzins über 1 % | −0,24 | +0,30 |
| Konjunktur schwach | −0,28 | +0,60 |
| Konjunktur stark | −0,05 | +0,50 |

Die Vorzeichen kippen. In der ersten Hälfte war die Liquidität bei hohem Realzins **negativ** korreliert, in
der zweiten deutlich positiv. Damit fällt die Begründung für die Regel in sich zusammen: Der Unterschied
zwischen den Umfeldern ist kleiner als der Unterschied zwischen den Jahrzehnten.

Dazu kommt die Verwechslungsgefahr. Negative Realzinsen gab es überwiegend von 2011 bis 2021, Realzinsen über
ein Prozent fast nur ab 2023. "Umfeld" und "Zeitraum" sind hier kaum zu trennen. Eine Regel, die auf diese
Aufteilung baut, hätte in den Daten eine Vergangenheit nachgezeichnet, keine Gesetzmäßigkeit gefunden.

Mit 14 bis 30 unabhängigen Fenstern je Umfeld ist ein Unterschied von 0,3 in der Korrelation ohnehin nicht
von Zufall zu unterscheiden.

## 5. Was stattdessen trägt: feste, aber ausgewogenere Gewichte

Geprüft mit der echten Modellkette, also inklusive Overlays, Deckel, Vetos und Rang-Umrechnung. Das ist die
Zahl, die das Tool tatsächlich anzeigt.

Rangkorrelation des Rangs zur Rendite der folgenden 13 Wochen:

| Gewichtung Liquidität/Konjunktur/Struktur | gesamt | bis 2017 | ab 2018 | Abstand |
|---|---|---|---|---|
| aktuell 55/15/30 | +0,25 | +0,03 | +0,39 | 0,35 |
| ausgewogen 40/15/45 | +0,27 | +0,08 | +0,40 | 0,32 |
| struktur-schwer 30/15/55 | **+0,28** | **+0,09** | +0,40 | **0,31** |
| gleich 34/33/33 | +0,20 | +0,06 | +0,30 | 0,24 |

Auf 26 Wochen dasselbe Bild: 30/15/55 liefert +0,30 gesamt und +0,11 in der ersten Hälfte, die heutigen
Gewichte +0,28 und +0,07.

Gewicht von der Liquidität zur Struktur zu verschieben verbessert also **alle drei** Messgrößen gleichzeitig:
den Gesamtwert, den Wert in der schwachen ersten Hälfte und die Stabilität zwischen den Hälften. Der Effekt
ist klein, aber er zeigt in jeder einzelnen Auswertung in dieselbe Richtung.

**Die eigentliche Begründung ist aber nicht dieser Messwert.** Ihn als Beleg zu nehmen wäre derselbe Fehler
wie bei den Umfeld-Regeln: Auch er stammt aus demselben Datensatz. Die tragfähige Begründung ist eine andere:
Wenn man nicht zuverlässig sagen kann, welcher Treiber der wichtigste ist, soll man das Gewicht nicht auf
einen konzentrieren. Genau das ist hier der Fall, und die ausgewogenere Verteilung ist die Antwort darauf.

## 6. Was über beide Hälften hält

Nur zwei Bausteine zeigen in beiden Zeiträumen dasselbe Vorzeichen:

| Baustein | bis 2017 | ab 2018 | Rolle im Modell |
|---|---|---|---|
| Bewertung | +0,18 | +0,17 | Overlay, Deckel nach oben |
| Marktmechanik | −0,30 | −0,16 | Overlay, Kontra-Korrektur |

Das ist eine unerwartete Bestätigung des Aufbaus: Die beiden Bausteine, die **nicht** in den Score eingehen,
sind die einzigen mit stabilem Vorzeichen. Die Marktmechanik ist über den ganzen Zeitraum der stärkste
Einzelindikator überhaupt, und zwar negativ. Ihre Rolle als Kontra-Signal ist damit doppelt belegt.

## 7. Empfehlung

**Erstens, keine umfeldabhängigen Gewichte einbauen.** Die Belege dafür sind schwächer als die Belege für
feste Gewichte. Jede Regel, die sich aus den Umfeld-Tabellen ableiten ließe, dreht in der anderen Zeithälfte
das Vorzeichen. Das Tool wäre danach komplizierter und schlechter.

**Zweitens, die Gewichte ausgewogener verteilen**, etwa 40/15/45 statt 55/15/30. Nicht weil es besser misst,
sondern weil wir nicht wissen, welcher Treiber führt. Wer das nicht weiß, konzentriert nicht.

**Drittens, die Zeitraum-Abhängigkeit im Tool zeigen.** Das ist die ehrliche Form der Antwort auf "hängt das
von der Situation ab": Nicht als automatische Umgewichtung, sondern als sichtbarer Hinweis, dass die
Trefferquote des Modells vor 2018 deutlich schwächer war. Der Erwartungsblock nennt bereits das Prüf-Fenster
ab 2019; ein Satz zur ersten Hälfte gehört daneben.

**Viertens, die Konjunktur nicht aufwerten.** Sie liefert für sich genommen nichts (+0,03 auf 13 Wochen,
−0,06 auf 26) und behält ihre 15 Prozent nur als Qualifier für die Zyklusphase. Die Modellkette braucht sie
ohnehin, weil die Phase aus Liquiditäts- und Konjunkturrichtung entsteht.

## 8. Was diese Untersuchung nicht kann

Sie prüft nur den S&P 500, nur ab 2008 und nur mit heute gültigen, teils nachträglich revidierten Daten. Ein
Zeitraum mit anhaltend hoher Inflation wie 1970 bis 1982 fehlt vollständig, und gerade dort wäre die Frage
nach dem Vorrang von Liquidität gegen Struktur am interessantesten. Alles hier Gesagte gilt für ein einziges
Marktregime mit zwei scharfen Einbrüchen.
