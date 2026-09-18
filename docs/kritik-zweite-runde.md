# Zweite Begutachtung, drei Blickwinkel

Stand: 19.09.2026, begutachtet wurde die ausgelieferte Fassung unter hias95.github.io/MacroPilot-tool
(Lauf 8, Datenstand 18.09.2026, Gewichte 40/15/45, Rang 65, Zone Neutral).

Dieselben drei Personen wie am 18.09.2026, damit der Vergleich trägt, aber mit geschärfter Lebenslage:

- **Lena, Anfang 30, erster Sparplan.** Zahlt monatlich in einen Welt-ETF, hat noch nie einen Crash erlebt.
- **Bernd, Mitte 50, seit fünfzehn Jahren dabei.** Sechsstelliges Depot, denkt gerade über Umschichten nach.
- **Eine Fondsmanagerin.** Verwaltet fremdes Geld, muss jede Zahl vor einem Ausschuss vertreten.

Methode wie beim ersten Mal: beide Modi vollständig gelesen, jede Auffälligkeit gegen `dashboard.json`,
`backtest.json` und `meta.json` der Live-Seite nachgerechnet.

## 1. Was messbar besser geworden ist

Bevor die Kritik kommt, der faire Teil. Alles davon war vorher nicht da:

| Vorher | Jetzt |
|---|---|
| Drei Hinweise gleichrangig nebeneinander | Ein Gewichtungssatz ordnet sie: Zeitpunkt gegen Fallhöhe |
| "Letzte 365 Tage: keine Wechsel" bei drei Tagesbildern | "Aufgezeichnet seit 16.09.2026, 3 Tage" |
| "2 von 2" bei drei Kriterien | "2 von 3 erfüllt, nötig 2" |
| Deckel als Warnung, obwohl er nicht greift | "Deckel 66 greift nicht" |
| Kein Datenalter | "älteste Zahl 17 Tage alt", je Kachel das eigene Alter |
| Kein Wort zur Konzentration | "Net Liquidity 20 Prozent, Notenbanken 32 Prozent" |
| Trefferquote ohne Unsicherheit | "die Stichprobe lässt 6 bis 9 von 10 zu" |
| Nichts über andere Anlagen | Gold, Anleihen, Mischung mit gemessener Trennschärfe |
| Nichts über die Modellgüte im Zeitverlauf | "bis 2018 kaum (0,13), ab 2019 deutlich (0,39)" |

Der Einfach-Modus ist dabei mit 834 Wörtern nicht aufgebläht worden, der Profi-Modus hat 2966. Die
Befürchtung, es werde nur mehr statt besser, hat sich nicht bestätigt.

## 2. Lena, Anfang 30, erster Sparplan

**Ein Satz zerstört das Vertrauen sofort.** Im Erwartungsblock steht wörtlich:

> Bestätigte der Markt dabei das Bild, wie jetzt: **8 von 10 statt 8 von 10 sonst.** 56 Phasen

Das ist offensichtlicher Unsinn und steht direkt unter der wichtigsten Aussage der Seite. Ursache
nachgerechnet: Die Trefferquoten sind 84,0 und 78,3 Prozent. Der Unterschied überschreitet die eingebaute
Schwelle von fünf Punkten, also hält das Tool ihn für erwähnenswert, aber gerundet ergeben beide Werte 8.
Verglichen wird auf Hundertsteln, angezeigt wird in Zehnteln.

**Das Tool widerspricht sich zwischen den Modi.** Im Einfach-Modus steht bei der Fiskalischen Dominanz
"Historisch profitieren Sachwerte und Gold". Im Profi-Modus misst dasselbe Tool für Gold eine Trennschärfe
von +0,03, also praktisch null, und schreibt dazu "bei Gold und Anleihen dagegen praktisch nicht". Lena
liest nur den Einfach-Modus und nimmt eine Behauptung mit, die die eigenen Daten nicht stützen.

**Kommazahlen mit Punkt.** "+11.3 Punkte", "(0.13)", "(+0.27)". In einer deutschsprachigen Oberfläche, die
sonst überall "+17,4 Pkt." schreibt, sieht das nach Maschine aus, nicht nach Sorgfalt. Betroffen sind genau
die drei zuletzt gebauten Bausteine.

**Was gut funktioniert:** Der Gewichtungssatz nimmt ihr die Arbeit ab, die drei Warnungen zu sortieren. Die
Lesehilfe beantwortet genau die Fragen, die sie stellen würde. Der Block "Worüber dieses Tool nichts sagt"
ist für sie der wichtigste auf der Seite, weil er den Fehlschluss verhindert, das Ding sage etwas über ihren
Welt-ETF.

## 3. Bernd, Mitte 50, seit fünfzehn Jahren dabei

**Die Zonentabelle widerlegt sich in der letzten Spalte.** Nach 52 Wochen sieht die Reihenfolge so aus:

| Zone | nach 13 Wochen | nach 52 Wochen |
|---|---|---|
| Stark negativ | +1,3 % | +11,3 % |
| Negativ | +3,4 % | +13,6 % |
| Neutral | +3,9 % | +15,9 % |
| **Positiv** | +4,2 % | **+8,7 %** |
| Stark positiv | +10,0 % | +32,3 % |

Auf Jahressicht ist ausgerechnet "Positiv" die schlechteste aller fünf Zonen, schlechter als "Stark negativ".
Die Spalte steht unkommentiert da. Bernd sieht das in zehn Sekunden und schließt daraus, dass die Leiter
nicht trägt.

**Die Zonen sind statistisch nicht unterscheidbar, und das Tool weiß es.** Die Unsicherheitsspannen, die seit
gestern berechnet werden, überlappen fast vollständig: Negativ 53 bis 90, Neutral 60 bis 92, Positiv 49 bis
97. Angezeigt wird die Spanne aber nur für die aktuelle Zone im Erwartungsblock, nicht in der Tabelle, wo man
die Zonen nebeneinander sieht. Die ehrlichste Aussage der ganzen Anwendung bleibt damit verborgen.

**Die Vergangenheit wurde still umgeschrieben.** Seit gestern gelten 40/15/45. Die Seite sagt trotzdem "seit
9 Wochen in dieser Zone", als hätte das Modell diese Zone neun Wochen lang angezeigt. Tatsächlich ist die
ganze Historie mit den neuen Gewichten neu berechnet. Die Parameterkennung im Modell-Panel ändert sich zwar,
aber nirgends steht, ab wann sie gilt und was vorher galt.

**Die Konzentration ist verschoben, nicht beseitigt.** Struktur & Fiskus wiegt jetzt 45 Prozent, und ihr
zweitgrößter Bestandteil, der Realzins, steht bei 6 von 100, also fast am Anschlag. Kehrt er auf einen
mittleren Wert zurück, steigt der Kern um rund fünf Punkte, ohne dass sich sonst etwas ändert. Der Score
hängt damit nicht mehr an der Fed-Bilanz, sondern spürbar an einer einzigen Zinsreihe.

## 4. Die Fondsmanagerin

**Der Nachweis fehlt weiterhin, nur ehrlicher.** Der Ära-Hinweis sagt jetzt selbst, dass das Modell bis 2018
kaum getrennt hat. Das ist genau die Zahl, die sie zuerst gesucht hätte, und sie steht freiwillig da. Damit
ist die Anwendung ehrlicher als die meisten kommerziellen Produkte. Ihre Schlussfolgerung bleibt trotzdem:
Ein Modell, dessen Trennschärfe in der ersten Hälfte bei 0,13 liegt und in der zweiten bei 0,39, hat keinen
nachgewiesenen Vorteil, sondern eine Phase, die zu ihm passte.

**Sechs Phasen in der obersten Zone.** "Stark positiv" kommt in 7,5 Prozent der Wochen vor und beruht auf
sechs getrennten Aufenthalten. Die ausgewiesene Spanne von 51 bis 100 Prozent ist korrekt und sagt genau das:
Man weiß es nicht. In der Zonentabelle steht daneben aber weiterhin die glatte 98,4 Prozent als Hauptzahl.

**Kein Punkt-in-der-Zeit-Nachvollzug.** Die Tagesbilder gibt es erst seit dem 16.09.2026, drei Stück. Das
Erwartungsprotokoll seit dem 18.09., ein Eintrag. Ab jetzt ist beides sauber, für alles davor gibt es keine
Rekonstruktion dessen, was das Werkzeug tatsächlich angezeigt hat. Das ist unvermeidbar und sollte gesagt
werden, statt dass die Historie durchgehend so aussieht, als sei sie damals so gezeigt worden.

**Die Erklär-Schnittstelle ist defekt.** Im Profi-Modus steht unter jeder Säule "KI nicht verfügbar (gemini:
Gemini-API-Fehler 404)". Der regelbasierte Ersatztext greift und ist gut, das System funktioniert also. Aber
die Kopfzeile meldet weiterhin Gemini als Anbieter, und ein 404 deutet auf einen Modellnamen hin, den es
nicht mehr gibt. Ein Ausfall, der seit unbekannter Zeit läuft und nirgends auffällt, ist ein Betriebsmangel.

**Was sie anerkennen würde:** Die Konzentrationsangabe, die Unsicherheitsspannen, die getrennte Ausweisung
des Prüf-Fensters, die benannten Grenzen des Rückblicks und die Weigerung, umfeldabhängige Gewichte
einzubauen. Das ist methodisch sauberer als der erste Entwurf.

## 5. Nachgerechnete Mängel

| Nr. | Mangel | Befund |
|---|---|---|
| N1 | "8 von 10 statt 8 von 10 sonst" | Vergleich auf Hundertsteln (84,0 gegen 78,3), Anzeige in Zehnteln. Die Schwelle greift, der Unterschied verschwindet beim Runden. |
| N2 | Dezimalpunkt statt Komma | "+11.3 Punkte", "(0.13)", "(+0.27)" in Attribution, Ära-Hinweis und Anlagenvergleich. Der Rest der Oberfläche schreibt Komma. |
| N3 | Widerspruch zwischen den Modi | Einfach: "Historisch profitieren Sachwerte und Gold". Profi: Gold-Trennschärfe +0,03, "praktisch nicht". |
| N4 | 52-Wochen-Spalte widerlegt die Leiter | "Positiv" mit +8,7 % schlechter als "Stark negativ" mit +11,3 %, ohne Kommentar. |
| N5 | Unsicherheit nur an einer Stelle | Die Spannen überlappen fast vollständig (Negativ 53-90, Neutral 60-92, Positiv 49-97), stehen aber nicht in der Zonentabelle. |
| N6 | Gemini liefert 404 | Regelbasierter Ersatz greift, Kopfzeile meldet trotzdem Gemini. Fehler faellt sonst nirgends auf. |
| N7 | "Marktmechanik ruhig (-1 Punkte)" | Einzahl mit Pluralwort. |
| N8 | Historie still umgeschrieben | "seit 9 Wochen in dieser Zone" nach der Umgewichtung von gestern; kein Hinweis, ab wann welche Parameter gelten. |
| N9 | Konzentration verschoben | Struktur wiegt 45 %, ihr Realzins-Bestandteil steht bei 6 von 100. Eine Rückkehr auf 50 hebt den Kern um 5 Punkte. |

## 6. Verbesserungen nach Priorität

### Stufe E: sichtbar falsch (sofort)

| # | Maßnahme | Für wen | Aufwand |
|---|---|---|---|
| E1 | Bedingungs-Sätze auf gerundeten Werten vergleichen; bei gleicher Zehntelzahl "hat wenig geändert" sagen (N1) | alle | klein |
| E2 | Zahlen in Attribution, Ära-Hinweis und Anlagenvergleich mit deutschem Komma ausgeben (N2) | alle | klein |
| E3 | Die Gold-Behauptung im Regime-Hinweis durch die gemessene Zahl ersetzen oder streichen (N3) | Lena, Bernd | klein |
| E4 | Einzahl bei einem Punkt (N7) | alle | klein |

### Stufe F: Vertrauen sichern

| # | Maßnahme | Für wen | Aufwand |
|---|---|---|---|
| F1 | Unsicherheitsspanne in die Zonentabelle aufnehmen und dazuschreiben, dass sich die Zonen überlappen (N5) | Bernd, Fondsmanagerin | klein |
| F2 | Die 52-Wochen-Spalte kommentieren oder entfernen. Sie widerspricht der Leiter und beruht auf denselben wenigen Phasen (N4) | Bernd | klein |
| F3 | Modelländerungen datieren: eine kurze Liste "Was wurde wann geändert" neben der Parameterkennung, und ein Hinweis, dass die Historie mit den heutigen Parametern nachgerechnet ist (N8) | Fondsmanagerin | mittel |
| F4 | Gemini-Ausfall beheben und den Anbieter in der Kopfzeile nach dem tatsächlichen Ergebnis melden, nicht nach der Konfiguration (N6) | Betrieb | klein |

### Stufe G: Substanz

| # | Maßnahme | Für wen | Aufwand |
|---|---|---|---|
| G1 | Empfindlichkeit ausweisen: welcher Bestandteil den Score am stärksten bewegen würde, wenn er sich normalisiert (N9) | Bernd, Fondsmanagerin | mittel |
| G2 | Die Kalibriertafel bauen, sobald genug protokollierte Erwartungen vorliegen. Frühestens ab Mitte Dezember 2026 | alle | mittel |

## 7. Ein Satz zu jeder Person

**Lena** versteht die Seite jetzt und weiß, worüber sie nichts sagt. Ein einziger kaputter Satz und
Dezimalpunkte kosten mehr Vertrauen, als die vielen guten Sätze aufbauen.

**Bernd** bekommt endlich die Einordnung, die er selbst nicht rechnen konnte. Er stolpert dafür über die
52-Wochen-Spalte und fragt sich, warum die Unsicherheit nur an einer Stelle steht.

**Die Fondsmanagerin** hält das Werkzeug für methodisch ehrlich und inhaltlich unbewiesen. Beides stimmt,
und das Tool sagt es inzwischen selbst.
