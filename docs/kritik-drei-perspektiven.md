# Drei Blickwinkel auf MacroPilot: Einsteiger, erfahrener Privatanleger, Fondsmanager

Stand: 18.09.2026, Datenstand des geprueften Bildschirms ebenfalls 18.09.2026 (Rang 71, Zone Neutral seit
9 Wochen, Zyklusphase Aufschwung, Fiskalische Dominanz und Extreme Bewertung aktiv).

Methode: beide Modi vollstaendig gelesen, nicht ueberflogen, und jede Auffaelligkeit gegen die Rohdaten in
`dashboard.json`, `backtest.json` und `snapshots.json` geprueft. Was unten als Mangel steht, ist nachgerechnet,
nicht vermutet. Der Schwerpunkt liegt auftragsgemaess auf dem, was fehlt oder stoert.

## 1. Der Einsteiger

*Neu in der Investmentwelt, will verstehen, wie der Markt funktioniert, und daraus einen Schluss ziehen.*

**Das Grundproblem: Das Tool beantwortet eine andere Frage als die gestellte.** Der Einsteiger fragt "Was
bedeutet das fuer mich?", das Tool antwortet "So ist das Klima". Zwischen beidem liegt eine Luecke, die heute
nur der Haftungshinweis fuellt: "Anlageentscheidungen triffst du eigenverantwortlich." Das ist richtig und
soll auch so bleiben, aber es ist kein Ersatz fuer eine Denkhilfe. Ein Werkzeug darf keine Quoten empfehlen;
es darf und sollte aber zeigen, **welche Fragen** man sich bei dieser Lage stellt.

**Drei Ueberschriften widersprechen sich, ohne dass eine Rangfolge erkennbar waere.** Auf einem Bildschirm
stehen gleichzeitig:

- "Markt bestaetigt: Historisch die verlaesslichste Konstellation." (gut)
- "Extreme Bewertung aktiv: Die Fallhoehe ist maximal." (schlecht)
- "In 8 von 10 Wochen wie dieser stand der S&P 500 drei Monate spaeter hoeher." (gut)

Der Einsteiger hat kein Mittel, das zu gewichten. Es fehlt ein Satz, der die Widersprueche aufloest, etwa:
"Kurzfristig stuetzt mehr als bremst; das Risiko liegt nicht im Zeitpunkt, sondern in der Fallhoehe."

**Die Skalenrichtung ist nirgends erklaert.** Liquiditaet 55, Konjunktur 89, Bewertung 14. Dass ueberall
hoch = guenstig gilt, muss man erraten. Bei der Bewertung ist es besonders tueckisch: 14 heisst "extrem
teuer", die Zahl ist also das Gegenteil des Begriffs daneben. Im Einfach-Modus gibt es dazu keine Legende.

**Zahlenkollision bei der Liquiditaet.** Die Kachel zeigt den Score 55 und direkt darunter "Zaehlt 55 von 100
Punkten im Gesamtscore". Heute derselbe Wert aus reinem Zufall. Ein Einsteiger wird das fuer dieselbe Zahl
halten. Der Rollensatz war eine gute Ergaenzung, aber die Formulierung muss die Verwechslung ausschliessen.

**Die Tacho-Skala 0 / 10 / 30 / 70 / 90 / 100 steht unkommentiert da.** Warum die Abstaende ungleich sind
(es sind Quantile), erfaehrt man nur im Profi-Modus.

**Kein Wort dazu, worueber das Tool nichts sagt.** Es geht um den US-Aktienmarkt. Ein deutscher Einsteiger
mit einem Welt-ETF erfaehrt nicht, dass Waehrung, europaeische Konjunktur, Einzelwerte, Anleihen, Gold, Krypto,
Steuern und die eigene Lebenssituation komplett ausserhalb des Modells liegen. Das ist die wichtigste fehlende
Information ueberhaupt, weil sie Fehlschluesse verhindert.

**Fachbegriffe ohne Erklaerung** an sichtbarer Stelle: Rang, Zone, Perzentil, Zyklusphase, Overlay, Consensus,
Momentum. Im Profi-Modus kommen CAPE, Reverse Repo, TGA, SKEW, Backwardation, Terminstruktur dazu.

**Die Aenderungsliste ist leer und trotzdem prominent.** "Letzte 90 Tage: Keine Wechsel erkannt." Fuer den
Einsteiger ist das toter Raum, der aussieht wie eine Aussage ueber den Markt.

## 2. Der erfahrene Privatanleger

*Seit rund fuenfzehn Jahren investiert, kennt Zyklen, Bewertungskennzahlen und die ueblichen Irrtuemer.*

**Die Erwartung ignoriert genau das, was heute auffaellig ist.** Der Satz "8 von 10" gilt fuer die Zone
Neutral insgesamt, ueber 324 Wochen. Heute ist aber gleichzeitig die Bewertung im 94. Perzentil (CAPE) und im
100. Perzentil (Buffett). Die spannende Zahl waere die gemeinsame: Was folgte auf neutrale Wochen **bei
extremer Bewertung**? Das Tool hat alle Daten dafuer und zeigt sie nicht. So lange das fehlt, wirkt die
Erwartung beruhigender, als die Lage es hergibt.

**Man sieht nicht, welche Faktoren gerade ueberhaupt wirken.** Nachgerechnet: Kern 56,2, nach Mechanik 56,5,
Bewertungsdeckel 65,6. Der Deckel liegt **ueber** dem Wert, greift also nicht. Trotzdem steht "Extreme
Bewertung aktiv, Fallhoehe maximal" gross im Einfach-Modus und "Deckel bei 66" im Profi-Modus. Ein erfahrener
Leser will auf einen Blick sehen: bindend oder nicht. Dasselbe gilt fuer die Vetos, von denen heute keines
aktiv ist.

**Ein Sachverhalt, drei verschiedene Aussagen.** Zur Liquiditaet steht auf demselben Bildschirm:

| Ort | Aussage |
|---|---|
| Zyklusphase | "Liquiditaet steigt", "Liquiditaet und Konjunktur ziehen gemeinsam an" |
| Saeulentext | "Seit einem halben Jahr hat sich daran wenig geaendert" |
| Kennzahl | "52 W −0,80 %" |

Alle drei sind technisch korrekt (Richtung des Rohwerts, Perzentil des Momentums, Jahresveraenderung), aber
zusammen erzeugen sie Misstrauen statt Klarheit.

**Der Datenstand je Saeule schwankt zwischen einem und siebzehn Tagen** und wird nirgends als Einschraenkung
benannt: Liquiditaet 09.09., Konjunktur 01.09., Struktur 16.09., Bewertung 01.09., Mechanik 16.09.,
Marktsignale 17.09. Die mit 55 Prozent schwerste Saeule ist neun Tage alt. Oben steht schlicht "Stand
18.9.2026".

**Nur ein Vergleichsindex.** SPY. Kein Gold, keine Anleihen, kein 60/40, kein Welt-ETF in Euro. Gerade das
Regime-Flag "Fiskalische Dominanz" behauptet, Sachwerte und Gold profitierten historisch, belegt es aber mit
keiner einzigen Zahl. Eine Behauptung ohne Beleg im selben Werkzeug, das sonst alles belegt.

**Das wichtigste Negativergebnis steht unkommentiert in der Tabelle.** Die Regel mit Grundquote kostet 1,3
Prozentpunkte Rendite pro Jahr und spart beim groessten Rueckgang **exakt null** (−31,8 % gegen −31,8 %). Sie
senkt nur die Schwankung. Das ist ein ernstes Argument gegen den praktischen Nutzen der Zonen, und die
"Lesart" darunter geht darauf nicht ein, sondern spricht allgemein von "Schwankung gespart".

**Die Aenderungsliste behauptet mehr, als sie hat.** Ueberschrift "Letzte 365 Tage", Befund "Keine Wechsel
erkannt". Tatsaechlich liegen drei Tagesbilder vor. Der Leser schliesst auf ein ruhiges Jahr, obwohl das Tool
seit drei Tagen aufzeichnet.

**Kein Datenexport, keine Attribution ueber die Zeit.** Man kann nicht sehen, welcher Treiber den Score wann
bewegt hat, und die Zahlen nicht aus dem Werkzeug herausbekommen.

**"Erneut versuchen" unter den Erklaerungen ist im statischen Betrieb eine tote Schaltflaeche.** Sie kann dort
nie zu einem Ergebnis fuehren.

## 3. Der Fondsmanager

*Verwaltet fremdes Geld, muss jede Zahl vor einem Anlageausschuss vertreten koennen.*

**Es ist ein Ein-Faktor-Modell mit Verzierung.** Nachgerechnet: Net Liquidity ist 50 Prozent der
Liquiditaets-Saeule, die Saeule ist 55 Prozent des Kerns. Eine einzige Zeitreihe, WALCL minus TGA minus
Reverse Repo, bestimmt damit **27,5 Prozent des Gesamtscores**. Rechnet man den globalen Notenbank-Proxy
hinzu, haengen ueber 40 Prozent an Notenbankbilanzen. "Drei Treiber, drei Overlays" beschreibt die
Darstellung, nicht die Risikostruktur. Das gehoert offengelegt, sonst wirkt das Modell breiter als es ist.

**Die Statistik hat keine Fehlerbalken.** Ausgewiesen wird IC 0,25 auf 13 Wochen ueber 848 Wochen. Die
Fenster ueberlappen sich um zwoelf Dreizehntel; die effektive Zahl unabhaengiger Beobachtungen liegt bei
etwa 65, nicht 848. Ohne Standardfehler, t-Wert oder Konfidenzband ist ein IC von 0,25 auf diesem Zeitraum
nicht von Rauschen zu unterscheiden. Das Tool nennt die Zahl im Konzept, in der Oberflaeche gar nicht, und
an keiner Stelle ihre Unsicherheit.

**Die Bezugsklasse verschiebt sich unbemerkt.** Der Rang misst gegen die vorangegangenen zehn Jahre. Ein Rang
von 71 im Jahr 2026 wird gegen 2016 bis 2026 gemessen, also gegen eine Phase mit Nullzinsen und
Bilanzausweitung. Derselbe Rohwert haette 2013 einen anderen Rang ergeben. Das ist bei einem nicht-stationaeren
Umfeld eine erhebliche Einschraenkung und steht nirgends.

**In der Oberflaeche stehen Vollstichproben-Zahlen, kalibriert wurde walk-forward.** Die Zonentabelle und der
Strategievergleich laufen ueber 2010 bis 2026, also auch ueber den Zeitraum, aus dem die Gewichte stammen. Der
Nutzer sieht die geschmeichelte Variante. Die ehrliche Zahl aus dem Pruef-Fenster existiert, wird aber nicht
gezeigt.

**Finale Datenstaende statt Vintages.** CPI, die Regional-Fed-Umfragen und die Schuldendienstquote werden
revidiert. Der Backtest rechnet mit den heute gueltigen, revidierten Werten. Die eingebauten
Veroeffentlichungsverzoegerungen loesen das nicht: Sie verschieben den Zeitpunkt, nicht den Wert. Das ist ein
verbleibender Blick in die Zukunft, den ein Ausschuss sofort ansprechen wuerde. Im Konzept ist er erwaehnt, in
der Oberflaeche nicht.

**Ein einziges Regime.** 2010 bis 2026 enthaelt einen langen Bullenmarkt, zwei scharfe Rueckschlaege und keine
laengere Seitwaerts- oder Inflationsphase wie 1970 bis 1982. Die Zone "Stark positiv" beruht auf vier
getrennten Phasen. Jede Aussage ueber Extremzonen ist damit anekdotisch, und das gilt auch fuer die
Trefferquote von 100 Prozent, die in der Vergleichstabelle immer noch ohne diesen Vorbehalt steht.

**Keine Umsetzbarkeit.** Kein Positionsgroessen-Rahmen, keine Volatilitaetssteuerung, keine Korrelationen,
kein Umschlag, keine Kosten- und Steuerrechnung ausser einem Satz im Kleingedruckten. Die Zonenregeln im
Backtest sind Rechenbeispiele ohne Umsetzungslogik.

**Keine Aussage ausserhalb von Aktien.** Ein Makro-Modell dieser Bauart sollte etwas ueber Duration, Kredit,
Waehrung und Rohstoffe sagen koennen. Es sagt ausschliesslich "Umfeld fuer den S&P 500".

**Governance fehlt.** Keine sichtbare Modellversion, kein Aenderungsprotokoll der Parameter in der Oberflaeche,
keine Reproduzierbarkeitskennung neben den Zahlen. Wer im Nachhinein fragt, welche Gewichte am 18.09.2026
galten, findet die Antwort nur in der Git-Historie.

## 4. Nachgerechnete Maengel

Alles hier ist gegen die Rohdaten geprueft, nicht geschaetzt.

| Nr. | Mangel | Befund |
|---|---|---|
| M1 | Regime-Check zaehlt falsch | Anzeige "2 von 2" bei drei Kriterien, von denen zwei erfuellt und zwei noetig sind. Bei der Mechanik "0 von 1" bei zwei Kriterien. |
| M2 | Aenderungsliste behauptet ein Jahr | Ueberschrift "Letzte 365 Tage", tatsaechlich drei Tagesbilder vorhanden. |
| M3 | Bewertungsdeckel wirkungslos, aber prominent | Deckel 65,6 gegen Wert 56,5: greift nicht. Trotzdem als aktive Warnung dargestellt. |
| M4 | Drei Aussagen zur Liquiditaet | "steigt" gegen "wenig geaendert" gegen "52 W −0,80 %". |
| M5 | Datenalter unsichtbar | Spanne 1 bis 17 Tage, die schwerste Saeule 9 Tage alt, Kopfzeile sagt nur "Stand 18.9.2026". |
| M6 | Episoden nur an einer Stelle | Der Erwartungsblock nennt getrennte Phasen, die Vergleichstabelle weiter nur Wochen. |
| M7 | Tote Schaltflaeche | "Erneut versuchen" bei den Erklaerungen kann im statischen Betrieb nie gelingen. |
| M8 | Kopfzeile nennt die Erklaer-Engine | "Erklaerung: Ollama gemma3:12b" ist eine Angabe ueber die Exportumgebung, fuer den Leser bedeutungslos. |
| M9 | Zahlenkollision | Liquiditaet: Score 55 neben Gewicht "55 von 100 Punkten". |
| M10 | Skala unerklaert | Tacho-Marken 0/10/30/70/90/100 ohne Hinweis, dass es Quantile sind. |

## 5. Verbesserungen nach Prioritaet

Sortiert nach Schaden, den das Weglassen anrichtet, nicht nach Aufwand. Die Spalte "Fuer wen" nennt die
Perspektive, die am meisten davon hat: E = Einsteiger, P = Privatanleger, F = Fondsmanager.

### Stufe A: Was heute in die Irre fuehrt (zuerst)

Ein Werkzeug, das falsch zaehlt oder mehr behauptet als es hat, verliert genau die Glaubwuerdigkeit, von der
alles andere lebt. Diese Punkte sind klein im Aufwand und gross in der Wirkung.

| # | Massnahme | Fuer wen | Aufwand |
|---|---|---|---|
| A1 | Regime-Check richtig auszeichnen: "2 von 3 erfuellt, 2 noetig" statt "2 von 2" (M1) | alle | klein |
| A2 | Aenderungsliste ehrlich machen: "Aufzeichnung laeuft seit dem 16.09.2026" statt "Letzte 365 Tage" (M2) | alle | klein |
| A3 | Kennzeichnen, welche Faktoren gerade **bindend** sind: Deckel greift / greift nicht, Veto aktiv / inaktiv (M3) | P, F | klein |
| A4 | Eine Aussage pro Sachverhalt: Richtung, Momentum und Jahresveraenderung der Liquiditaet in einem Satz zusammenfuehren (M4) | alle | mittel |
| A5 | Datenalter sichtbar machen: aeltester Eingang in der Kopfzeile, Alter je Kachel (M5) | P, F | klein |
| A6 | Episodenzahl auch in der Vergleichstabelle, damit "100 %" nicht ohne Vorbehalt dasteht (M6) | P, F | klein |
| A7 | Tote Schaltflaeche und Engine-Angabe in der Kopfzeile entfernen (M7, M8) | alle | klein |

### Stufe B: Was den groessten Verstaendnisgewinn bringt

| # | Massnahme | Fuer wen | Aufwand |
|---|---|---|---|
| B1 | **Erwartung auf die Overlays bedingen**: nicht nur "Zone Neutral", sondern "Zone Neutral bei extremer Bewertung". Die Daten liegen vor, die Aussage aendert sich dadurch vermutlich deutlich | P, F | mittel |
| B2 | **Block "Worueber dieses Tool nichts sagt"**: Einzelwerte, Anleihen, Gold, Krypto, Europa, Waehrung, Steuern, die eigene Lage. Dauerhaft sichtbar, nicht im Kleingedruckten | E | klein |
| B3 | **Ein Satz, der die widerspruechlichen Hinweise gewichtet**, statt sie gleichrangig zu stapeln | E, P | mittel |
| B4 | **Erwartung taeglich mitspeichern**, damit spaeter eine echte Trefferbilanz moeglich ist. Zeitkritisch: jede nicht gespeicherte Woche ist verloren | P, F | klein |
| B5 | **Skalenlegende im Einfach-Modus**: hoch = guenstig, und bei der Bewertung ist die Zahl die Umkehrung des Begriffs | E | klein |
| B6 | **Begriffe erklaeren**, wo sie stehen: Rang, Zone, Perzentil, Overlay, Zyklusphase (M10 gleich mit) | E | mittel |
| B7 | Zahlenkollision aufloesen: Gewicht anders formulieren als den Score (M9) | E | klein |

### Stufe C: Substanz fuer den erfahrenen Anleger

| # | Massnahme | Fuer wen | Aufwand |
|---|---|---|---|
| C1 | Weitere Vergleichsmassstaebe: Gold, Anleihen, 60/40, Welt-ETF in Euro. Belegt nebenbei die Behauptung des Regime-Flags zu Sachwerten | P, F | mittel |
| C2 | Pruef-Fenster getrennt ausweisen statt nur Vollstichprobe | P, F | mittel |
| C3 | Treiber-Attribution ueber die Zeit: welcher Treiber hat den Score wann bewegt | P, F | mittel |
| C4 | Datenexport als CSV | P, F | klein |
| C5 | Das Negativergebnis der Grundquoten-Regel ausdruecklich benennen: kostet Rendite, spart beim groessten Rueckgang nichts | P | klein |

### Stufe D: Was ein Profi zuerst angreifen wuerde

| # | Massnahme | Fuer wen | Aufwand |
|---|---|---|---|
| D1 | **Konzentration offenlegen**: eine Zeitreihe bestimmt 27,5 Prozent des Scores, Notenbankbilanzen zusammen ueber 40 Prozent. Entweder breiter aufstellen oder deutlich dazuschreiben | F | klein (schreiben) bis gross (aendern) |
| D2 | **Unsicherheit beziffern**: effektive Stichprobe, Standardfehler oder Konfidenzband zu den Kennzahlen | F | mittel |
| D3 | **Verschiebung der Bezugsklasse benennen**: der Rang misst gegen ein wanderndes Zehn-Jahres-Fenster | F | klein |
| D4 | **Revisionen**: entweder Vintage-Daten nutzen oder die Einschraenkung in der Oberflaeche sagen, nicht nur im Konzept | F | klein (sagen) bis gross (ALFRED) |
| D5 | Aussagen ausserhalb von Aktien: Duration, Kredit, Waehrung, Rohstoffe | F | gross |
| D6 | Modellversion und Parameterstand neben den Zahlen sichtbar machen | F | klein |

## 5a. Stand der Umsetzung: Stufe A erledigt (18.09.2026)

Alle sieben Punkte der Stufe A sind umgesetzt und im Browser geprueft, in beiden Modi und auf Handybreite.

| # | Vorher | Nachher |
|---|---|---|
| A1 | "2 von 2" bei drei Kriterien | "2 von 3 erfuellt, noetig 2"; inaktive Flags "0 von 2 erfuellt, noetig 1" |
| A2 | "Letzte 365 Tage: Keine Wechsel erkannt" | "Aufgezeichnet seit 16.09.2026, 3 Tage" und "Seit Beginn der Aufzeichnung ... hat sich nichts geaendert" |
| A3 | "Bewertung · Deckel 66" | "Deckel 66 greift nicht", im Warum-Text "Er greift derzeit nicht, der Rohwert liegt mit 56 darunter", dazu "Kein Veto aktiv" |
| A4 | "Liquiditaet steigt" neben "wenig geaendert" | abgestufte Kurzform aus einer Quelle: "Liquiditaet kaum veraendert", "Konjunktur steigt deutlich"; der Phasentext beschreibt jetzt die Phase ("Aufschwung heisst: ...") statt die Woche |
| A5 | nur "Stand 18.9.2026" | Kopfzeile "aelteste Zahl 17 Tage alt", je Kachel "Stand 09.09.2026, 9 Tage alt" |
| A6 | "156 W." | "25 Phasen", bei Stark positiv "4 Phasen" in Bernstein |
| A7 | tote Schaltflaeche, "Erklaerung: Ollama gemma3:12b" | Hinweis statt Schaltflaeche im statischen Betrieb; die Engine-Angabe ist dem Datenalter gewichen |

Technisch dahinter: `store.first_snapshot_date()` fuer den Aufzeichnungsbeginn, `oldest_input` als Meta-Wert
beim Refresh, `ConsensusResponse.cap_binding`, `liquidity_move` / `growth_move` aus einer gemeinsamen
Abstufung (`consensus.direction_words`, gleiche Schwellen wie `easy.py`), und ein zentraler Alters-Helfer in
`format.ts` mit festem Bezugszeitpunkt pro Seitenaufruf. Abgerundet statt gerundet, sonst waere eine Zahl vom
1. am Nachmittag des 18. als achtzehn Tage alt ausgewiesen worden.

## 6. Ein Satz zu jeder Perspektive

**Einsteiger:** Er versteht nach dem Besuch mehr ueber den Markt als vorher, aber nicht mehr ueber seine
eigene Lage. Die Luecke laesst sich schliessen, ohne Beratung zu werden, naemlich durch Fragen statt Antworten
und durch eine klare Ansage, worueber das Tool schweigt.

**Privatanleger:** Er bekommt eine saubere, nachvollziehbare Zusammenfassung des Umfelds, vermisst aber genau
die Verknuepfung, die er selbst nicht hinbekommt: was die Bewertung mit der Zone macht, und ob ein Faktor
heute ueberhaupt wirkt.

**Fondsmanager:** Er wuerde das Modell nicht ablehnen, aber zurueckstufen. Es ist ein gut gebautes
Liquiditaets-Modell mit ehrlicher Darstellung und drei Schwaechen, die er zuerst ansprechen wuerde:
Konzentration auf eine Zeitreihe, fehlende Fehlerbalken und revidierte Daten im Rueckblick.
