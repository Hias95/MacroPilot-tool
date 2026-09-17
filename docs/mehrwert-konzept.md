# Vom Zustandsanzeiger zum Erwartungswerkzeug

Stand: 17.09.2026. Ausloeser: Das Tool liefert viele richtige Zahlen, aber der Nutzer hat nicht das Gefuehl,
danach besser einschaetzen zu koennen, was gerade passiert ist und was als Naechstes kommt. Dieses Dokument
benennt die Ursachen, fasst zusammen, was aus der Forschung zur Risikokommunikation dazu belegt ist, und
arbeitet konkrete Bausteine aus. Es ist ein Vorschlag, noch keine Umsetzung.

## 1. Befund: Was heute auf dem Bildschirm steht

Der Startbildschirm im Einfach-Modus sagt heute sinngemaess sieben Mal dasselbe in verschiedenen Worten:
"So ist die Lage." Er sagt kein einziges Mal: "Das folgte darauf", "das hat sich bewegt", "darauf kommt es
als Naechstes an."

Konkret, am realen Bildschirm vom 17.09.2026 nachgezaehlt:

| Element | Aussage | Zeitrichtung |
|---|---|---|
| Tacho 75 | Rang gegenueber zehn Jahren | Gegenwart |
| Zonenwort "Neutral" | bestaetigte Ampelstufe | Gegenwart |
| "seit 9 Wochen in dieser Zone" | Dauer | Vergangenheit, ohne Folge |
| Zyklusphase "Aufschwung" | Qualifier | Gegenwart |
| "Markt bestaetigt" | Overlay | Gegenwart |
| "Fiskalische Dominanz aktiv" | Regime | Gegenwart |
| "Extreme Bewertung aktiv" | Regime | Gegenwart |
| Verlaufschart | Rangkurve | Vergangenheit, ohne Deutung |

Vier Probleme fallen dabei sofort auf.

**Erstens widerspricht sich der Tacho selbst.** Die Nadel steht auf 75 und damit sichtbar im gruenen Feld,
das Wort darunter heisst "Neutral" und ist gelb. Die Aufloesung kommt drei Zeilen spaeter im Kleingedruckten
("Diese Woche zeigt bereits Positiv, die Zone wechselt erst nach drei Wochen in Folge"). Der erste Eindruck
ist also ein Widerspruch, den der Nutzer erst durch Lesen aufloesen muss. Das kostet genau das Vertrauen,
das ein Ueberblicksbild schaffen soll.

**Zweitens fehlt die Bezugsklasse.** "Besser als 75 Prozent der Wochen der letzten zehn Jahre" ist ein Rang,
kein Ergebnis. Der Nutzer kann daraus nicht ableiten, was das fuer ihn bedeutet. Ein Rang beantwortet
"wie ungewoehnlich ist die Lage", nicht "was folgte auf solche Lagen".

**Drittens ist das einzige nach vorn gerichtete Element ganz unten vergraben.** Die Tabelle, was nach jeder
Ampelzone historisch folgte, existiert seit gestern, steht aber am Ende der Profi-Ansicht und ist als
Rueckblick auf ein Backtest-Verfahren gerahmt. Fuer den Einfach-Modus existiert sie gar nicht.

**Viertens stehen widerspruechliche Hinweise gleichwertig nebeneinander.** "Markt bestaetigt" ist ein gutes
Zeichen, "Extreme Bewertung" und "Fiskalische Dominanz" sind Warnungen. Alle drei stehen untereinander in
gleicher Schriftgroesse. Der Nutzer muss selbst gewichten, und genau das kann er nicht.

## 2. Was die Forschung dazu sagt

Fuenf Befunde aus der Risiko- und Unsicherheitskommunikation, die sich direkt auf dieses Tool uebertragen
lassen. Quellen am Ende des Dokuments.

**Die Bezugsklasse entscheidet, nicht die Zahl.** Die Wetterforschung hat das am Regenrisiko sauber gezeigt:
Menschen verstehen "30 Prozent" problemlos, scheitern aber daran, worauf sich die 30 Prozent beziehen. Die
verstaendliche Formulierung nennt die Bezugsklasse mit: "An 3 von 10 Tagen wie morgen regnet es." Uebertragen:
nicht "Rang 75", sondern "In 8 von 10 Wochen wie dieser stand der Index drei Monate spaeter hoeher."

**Natuerliche Haeufigkeiten schlagen Prozentwerte.** Gigerenzers Arbeiten und die darauf aufbauende Literatur
zeigen, dass "8 von 10" besser verstanden wird als "80 Prozent", besonders bei geringer Zahlenaffinitaet, und
dass abzaehlbare Symbole die Wahrnehmung zusaetzlich stuetzen.

**Haeufigkeitsbasierte Verteilungsbilder verbessern Entscheidungen messbar.** Im kontrollierten Experiment von
Fernandes, Walls, Munson, Hullman und Kay fuehrten Quantil-Punktdiagramme zu besseren und stabileren
Entscheidungen als Text oder Dichtekurven. Ein Streifen aus 20 Punkten, von denen 16 gruen und 4 rot sind,
wirkt also nachweislich besser als eine glatte Kurve oder eine Spanne.

**Wort und Zahl gehoeren zusammen, jedes Mal.** Die Auswertungen der IPCC-Wahrscheinlichkeitsbegriffe zeigen,
dass Leser Begriffe wie "wahrscheinlich" deutlich zuverlaessiger treffen, wenn die Zahl direkt danebensteht,
und nicht nur in einer Legende weiter hinten. Ausserdem verzerren negativ formulierte Wahrscheinlichkeiten das
Urteil staerker als positiv formulierte.

**Offen zugegebene Unsicherheit kostet kaum Vertrauen.** Die Untersuchungen von Spiegelhalter und der
Gruppe um van der Bles zeigen, dass numerisch ausgedrueckte Unsicherheit das Vertrauen nur geringfuegig
senkt. Die praktischen Regeln daraus: einfache Sprache, nur das Noetige, den Zeitraum immer ausdruecklich
nennen, und die eigene Unsicherheit benennen statt zu verstecken.

Dazu kommt der Befund aus der Dashboard-Praxis, der weniger wissenschaftlich, aber einhellig ist: Eine
Ueberschrift soll die Erkenntnis nennen, nicht die Achse beschriften. "Liquiditaet 68" ist eine Beschriftung.
"Die Liquiditaet traegt den Score, aber sie dreht seit drei Wochen" ist eine Erkenntnis.

## 3. Die Leitidee: drei Fragen statt einer Zahl

Das Tool beantwortet heute eine Frage: "Wie ist die Lage?" Der empfundene Mehrwert entsteht erst, wenn es
drei beantwortet, in dieser Reihenfolge:

1. **Was ist gerade passiert?** Eine Chronik der letzten Woche mit Ursache, nicht nur ein Zustand.
2. **Was folgte historisch auf solche Lagen?** Eine Erwartung mit Bezugsklasse, Zeitraum und Spannweite.
3. **Woran erkenne ich, dass es kippt?** Auslöser, Schwellen und Termine, auf die man warten kann.

Diese drei Fragen sind die Gliederung fuer alles Weitere. Jede ist mit vorhandenen Daten beantwortbar; keine
davon erfordert eine neue Datenquelle oder laufende Kosten.

## 4. Die Bausteine

Die eingerueckten Bloecke sind Formulierungsentwuerfe, keine Ausgaben des Tools. Zahlen darin sind
Platzhalter, ausser wo ausdruecklich auf vorhandene Werte verwiesen wird. Was heute schon berechnet ist
und was noch fehlt, steht jeweils unter *Datenlage*.

### A. Die Erwartung: "Was folgte auf Wochen wie diese?"

**A1 Der Erwartungssatz ganz oben.** Direkt unter dem Tacho, vor allen Details, ein Satz nach dem Muster der
Wetterkommunikation, mit Wort und Zahl zusammen und ausdruecklichem Zeitraum:

> In **8 von 10** Wochen wie dieser stand der S&P 500 **drei Monate spaeter** hoeher.
> Mittelwert **+3,6 %**, im schlechtesten Zehntel **-6 %**, im besten **+12 %**.
> Grundlage: 324 vergleichbare Wochen seit 2010.

Das ersetzt den Rang nicht, es uebersetzt ihn. Der Rang bleibt als Nebeninformation stehen.

*Datenlage:* Trefferquote und Mittelwert liegen bereits in `backtest.json` je Zone. Fehlend sind die
Perzentile der Vorwaertsrendite und die Zahl unabhaengiger Episoden. Beides ist eine kleine Ergaenzung in
`backend/app/backtest.py`.

*Fallstrick:* Die Wochen ueberlappen sich. 53 Wochen in "Stark positiv" sind vielleicht fuenf oder sechs
unabhaengige Episoden, und die dort ausgewiesenen 100 Prozent Trefferquote sind entsprechend duenn belegt.
Der Erwartungssatz muss deshalb die Zahl der Episoden nennen und bei duenner Datenlage ausdruecklich
zurueckhaltender formulieren. Sonst verkauft das Tool Zufall als Gesetz.

**A2 Der Ergebnisstreifen statt einer Kurve.** Unter dem Satz zwanzig Punkte in einer Reihe, gefuellt nach
dem historischen Ausgang: sechzehn gruen, vier rot. Darunter die Beschriftung "20 vergleichbare Wochen,
so ging es aus". Genau diese Darstellung hat im Experiment am besten abgeschnitten, weil man sie abzaehlen
kann. Eine Dichtekurve oder ein Faecherdiagramm waere fachlich gleichwertig und praktisch schlechter.

*Datenlage:* Ergibt sich aus denselben Quantilen wie A1. Reine Frontend-Arbeit.

**A3 Der Zeitraum steht immer dabei.** Der ehrliche Horizont des Modells sind drei bis sechs Monate: die
Rangkorrelation zum Vorwaertsertrag liegt bei 13 Wochen bei +0,25 und bei 26 Wochen bei +0,28, auf vier
Wochen dagegen nur bei +0,14. Das Tool darf also nie so wirken, als sage es die naechste Woche vorher. Der
Zeitraum gehoert in jeden Erwartungssatz und in jede Ueberschrift.

### B. Die Chronik: "Was ist gerade passiert?"

**B1 Die Bewegung der Woche mit Ursache.** Heute steht dort ein Zustand. Stattdessen: welche drei
Teilindikatoren den Gesamtwert in dieser Woche am staerksten bewegt haben, mit Vorzeichen und Beitrag in
Punkten.

> Diese Woche **+4 Punkte**. Getragen von der Liquiditaet: Die Notenbankbilanzen haben um 41 Mrd. USD
> zugelegt (**+3,1 Pkt.**). Gegenlaeufig: Der Realzins ist gestiegen (**-0,8 Pkt.**).

*Datenlage:* Berechenbar aus der vorhandenen Wochenhistorie, indem der Gesamtwert einmal mit dem Vorwochen-
Wert je Treiber nachgerechnet wird. Die Differenz ist der Beitrag. Backend, mittlerer Aufwand, keine neuen
Daten.

**B2 Die Ereignisliste bekommt Folgen.** Die Liste "Was hat sich geaendert?" nennt heute Wechsel ohne
Konsequenz. Jeder Eintrag sollte zeigen, was seitdem passiert ist: "Zone auf Neutral gewechselt am 15.07.
Der Index steht seitdem +2,4 %." Das macht die Chronik ueberpruefbar und nimmt ihr den Beipackzettel-Ton.

**B3 Ein Satz zur Woche.** Aus B1 und B2 laesst sich ein einziger Satz erzeugen, der oben steht und die Woche
zusammenfasst. Regelbasiert formuliert, nicht vom Sprachmodell, damit er immer verfuegbar und immer gleich
streng ist.

### C. Die Ausloeser: "Woran erkenne ich, dass es kippt?"

**C1 Die Kippschwelle.** Fuer jeden Treiber ausrechnen, wie weit er sich bewegen muesste, damit der Rang die
naechste Zonengrenze reisst, und das im Klartext nennen.

> Bis **Positiv** fehlen **2 Punkte**. Das entspricht etwa: Liquiditaet +6 Punkte, oder Struktur +4 Punkte,
> oder ein Wechsel der Marktbestaetigung.
> Nach **Negativ** waere es weit: Die Liquiditaet muesste um 19 Punkte fallen.

Das ist der Baustein, der am staerksten das Gefuehl erzeugt, die Mechanik verstanden zu haben, weil er die
Gewichte erfahrbar macht. Er sagt nichts vorher, er beschreibt nur die Hebel.

*Datenlage:* Reine Rechnung auf dem bestehenden Modell, jeder Treiber einmal variiert, bis die Zonengrenze
faellt. Backend, kleiner bis mittlerer Aufwand.

**C2 Der Terminkalender.** Was in den naechsten Tagen veroeffentlicht wird und welchen Treiber es beruehrt.

> **Mi 23.09.** Notenbankbilanz der Fed, woechentlich, wirkt auf Liquiditaet (Gewicht 55 %).
> **Do 24.09.** Philadelphia-Fed-Umfrage, wirkt auf Konjunktur (15 %).

Damit hat der Nutzer zum ersten Mal einen Grund wiederzukommen, und das Warten bekommt eine Richtung.

*Datenlage:* FRED liefert Veroeffentlichungstermine ueber die Release-Endpunkte der API, die mit dem
vorhandenen Schluessel kostenlos nutzbar sind. Fuer die uebrigen Quellen genuegen feste Regeln, etwa der
woechentliche Donnerstagsrhythmus der Fed-Bilanz. Mittlerer Aufwand, ein neuer Client.

**C3 Der Vorlauf.** Welcher Treiber laeuft historisch voraus und auf welchem Horizont. Das Tool rechnet die
Rangkorrelation je Saeule und Horizont im Backtest bereits aus; der Satz muss daraus erzeugt werden statt
gesetzt zu sein. Der bisherige Befund aus C1: Die Liquiditaet korreliert erst auf Jahressicht nennenswert mit
dem Vorwaertsertrag, die Struktur schon auf einem halben Jahr, die Konjunktur kaum. Daraus wird ein Satz wie
"Die Liquiditaet wirkt mit langem Vorlauf; dass sie heute stuetzt, muss in den Kursen noch nicht stehen."
Wichtig: Der Satz wird bei jeder Kalibrierung neu erzeugt, sonst veraltet er still.

### D. Die Einordnung: das Gefuehl, die Lage zu kennen

**D1 Die aehnlichsten Wochen der Geschichte.** Die drei Wochen seit 2008 mit dem aehnlichsten Profil ueber
alle Treiber und Overlays suchen und zeigen, was danach geschah.

> Am naechsten dran: **Maerz 2013**, **September 2016**, **Juli 2019**.
> Nach diesen drei Wochen lag der Index drei Monate spaeter bei +4,1 %, +1,2 % und -1,8 %.

Das ist der Baustein mit dem groessten Erlebniswert, weil er abstrakte Zahlen in erinnerbare Zeitpunkte
uebersetzt. Er ist zugleich der ehrlichste Umgang mit kleiner Stichprobe: drei Beispiele, die auseinander
gehen, zeigen die Spannweite besser als jeder Mittelwert.

*Datenlage:* Abstand ueber die sechs Score-Reihen auf dem bestehenden Wochenraster, kein neuer Datenbezug.
Mittlerer Aufwand.

**D2 Den Widerspruch im Tacho aufloesen.** Zwei Markierungen statt einer: die bestaetigte Zone als Feld, die
aktuelle Woche als zweite, duennere Nadel, und darunter ein Satz, der beides in einem Zug nennt.

> **Neutral**, seit 9 Wochen. Diese Woche bereits **Positiv**, bestaetigt waere der Wechsel am **6. Oktober**.

Das nennt sogar das Datum, ab dem es gilt. Aus einem Widerspruch wird eine Vorschau. Kleiner Aufwand, grosse
Wirkung.

**D3 Hinweise gewichten statt auflisten.** Die Regime-Flags und Overlays sollten nach Tragweite sortiert und
optisch abgestuft sein, mit einem einzigen zusammenfassenden Satz darueber: "Zwei Warnungen stehen gegen ein
bestaetigendes Signal; die Bewertung begrenzt das Aufwaertspotenzial, nicht das Timing."

### E. Das Vertrauen: die eigene Trefferquote zeigen

**E1 Kalibrierung offen ausweisen.** Wenn das Tool sagt "8 von 10", dann sollte nachpruefbar sein, wie oft
das gestimmt hat. Eine kleine Tafel mit den Aussagen der letzten Jahre und ihrem tatsaechlichen Ausgang.
Spiegelhalters Befund ist eindeutig: Offenheit ueber Unsicherheit kostet kaum Vertrauen, verdeckte Fehler
kosten es vollstaendig.

**E2 Die Grenzen als fester Bestandteil.** Ein dauerhaft sichtbarer, kurzer Absatz, was das Modell nicht
kann: keine Einzelwerte, keine Wochenprognose, keine Kriege und keine Notenbanksitzungen im Voraus. Das
schuetzt vor Enttaeuschung und ist zugleich die ehrlichste Form von Kompetenz.

## 5. Wie die Startseite danach aussieht

Der Einfach-Modus bekommt eine feste Dramaturgie von oben nach unten. Jeder Block beantwortet genau eine der
drei Fragen, und die Ueberschrift nennt die Erkenntnis, nicht die Achse.

| Reihenfolge | Block | Frage | Herkunft |
|---|---|---|---|
| 1 | Satz zur Woche | Was ist passiert? | B3 |
| 2 | Tacho mit zwei Markierungen und Wechseldatum | Wo stehen wir? | D2 |
| 3 | Erwartungssatz plus Ergebnisstreifen | Was folgte darauf? | A1, A2 |
| 4 | Kippschwelle | Woran erkenne ich den Wechsel? | C1 |
| 5 | Naechste Termine | Worauf warte ich? | C2 |
| 6 | Bewegung der Woche, drei Treiber | Warum hat es sich bewegt? | B1 |
| 7 | Aehnlichste Wochen | Kenne ich so etwas? | D1 |
| 8 | Die Saeulen wie bisher | Details | vorhanden |

Der Profi-Modus behaelt alles Bestehende und bekommt dieselben Bloecke in dichterer Form, dazu die
Kalibriertafel (E1) und die Zonentabelle, die jetzt unten steht.

## 6. Was wir bewusst nicht tun

- **Keine Kursziele und keine Prozentquoten.** Das war von Anfang an die Grenze und bleibt es. Der Unterschied
  zwischen "danach lag der Index in 8 von 10 Faellen hoeher" und "kauf jetzt" ist der ganze Unterschied
  zwischen Werkzeug und Beratung.
- **Keine Wochenprognose.** Der Horizont des Modells sind drei bis sechs Monate. Alles Kurzfristigere
  waere Scheingenauigkeit.
- **Keine erfundenen Wahrscheinlichkeiten.** Jede Zahl im Erwartungssatz kommt aus abgezaehlter Historie, nicht
  aus einem Modell ueber dem Modell. Wo die Stichprobe duenn ist, sagt das Tool das.
- **Keine vom Sprachmodell erzeugte Erwartung.** Gemini darf Zusammenhaenge erklaeren, aber niemals die Zahlen
  oder die Richtung setzen. Sonst ist die Kette nicht mehr pruefbar.
- **Keine Ampel, die zum Handeln auffordert.** Die Zonen beschreiben das Umfeld, nicht eine Aktion.

## 7. Vorschlag zur Reihenfolge

Nach Wirkung je Aufwand sortiert. Die ersten drei Schritte aendern den empfundenen Nutzen am staerksten und
sind zusammen ueberschaubar.

| Schritt | Baustein | Aufwand | Wirkung |
|---|---|---|---|
| 1 | D2 Tacho-Widerspruch aufloesen, mit Wechseldatum | klein | **erledigt 17.09.2026** |
| 2 | A1 und A3 Erwartungssatz mit Bezugsklasse und Zeitraum | klein, plus Perzentile im Backtest | **erledigt 17.09.2026** |
| 3 | A2 Ergebnisstreifen aus zehn Punkten | klein, reines Frontend | **erledigt 17.09.2026** |
| 4 | B1 und B3 Bewegung der Woche mit Ursache und Wochensatz | mittel | beantwortet "was ist passiert" |
| 5 | C1 Kippschwelle | mittel | macht die Mechanik begreifbar |
| 6 | C2 Terminkalender ueber die FRED-Release-API | mittel, neuer Client | gibt einen Grund wiederzukommen |
| 7 | D1 Aehnlichste Wochen | mittel | groesster Erlebniswert |
| 8 | D3, B2, E1, E2 Feinschliff, Gewichtung, Kalibrierung, Grenzen | klein bis mittel | Vertrauen |

Die Schritte 1 bis 3 sind fachlich unabhaengig voneinander und koennten in einem Zug umgesetzt werden. Alles
ist mit den vorhandenen kostenlosen Quellen machbar; nur C2 braucht einen zusaetzlichen, ebenfalls kostenlosen
Endpunkt derselben FRED-Schnittstelle.

## 7a. Was davon steht (17.09.2026)

Schritt 1 bis 3 sind umgesetzt und im Browser geprueft.

- **Tacho (D2):** Die bestaetigte Zone ist als farbiges Feld im Bogen sichtbar, darunter steht bei Abweichung
  "diese Woche <Zone>". Der Satz nennt jetzt das Datum: "bestätigt wäre der Wechsel am 27. September 2026,
  wenn es so bleibt." Backend: `ConsensusState` fuehrt die schwebende Zone mit, `ConsensusResponse` liefert
  `zone_pending_key`, `zone_pending_weeks`, `zone_confirm_weeks` und `zone_change_date`.
- **Erwartungssatz (A1, A3):** `frontend/src/components/dashboard/outlook-panel.tsx`, in beiden Modi direkt
  unter dem Tacho. Der Zeitraum steht im Satz, nicht in einer Legende.
- **Ergebnisstreifen (A2):** Zehn Punkte statt zwanzig, damit er eins zu eins zum Satz passt.
- **Ehrlichkeit bei duenner Datenlage:** `backtest.py` zaehlt jetzt `episodes`, also zusammenhaengende
  Aufenthalte je Zone, und liefert `p10/p50/p90`. Unter zehn Episoden faerbt sich der Grundlagensatz bernstein
  und nennt die Unsicherheit ausdruecklich. Das trifft "Stark positiv": 53 Wochen, aber nur vier Phasen.

## 8. Quellen

- Fernandes, Walls, Munson, Hullman, Kay: *Uncertainty Displays Using Quantile Dotplots or CDFs Improve
  Transit Decision-Making*, CHI 2018. https://dl.acm.org/doi/10.1145/3173574.3173718
- Padilla, Kay, Hullman: *Uncertainty Visualization*, Ueberblickskapitel.
  https://friendly.github.io/6135/papers/Uncertainty_Visualization_Padilla_Kay_Hullman_2020.pdf
- van der Bles, van der Linden, Freeman, Spiegelhalter: *The effects of communicating uncertainty on public
  trust in facts and numbers*, PNAS 2020. https://www.pnas.org/doi/10.1073/pnas.1913678117
- van der Bles et al.: *Communicating uncertainty about facts, numbers and science*, Royal Society Open
  Science 2019. https://royalsocietypublishing.org/rsos/article/6/5/181870/95102/
- Spiegelhalter: *Risk and Uncertainty Communication*.
  https://regulation.org.uk/library/2017-Spiegelhalter-Risk_and_Uncertainty_Communication.pdf
- NOAA: *Communicating Probability Information in Weather Forecasts*, zur Bezugsklasse beim Regenrisiko.
  https://repository.library.noaa.gov/view/noaa/60526/noaa_60526_DS1.pdf
- Gigerenzer: *What are natural frequencies?*
  https://pure.mpg.de/rest/items/item_2099208_9/component/file_3562683/content
- *Dimensions of uncertainty communication: What is conveyed by verbal terms and numeric ranges*, zu Wort und
  Zahl gemeinsam. https://pmc.ncbi.nlm.nih.gov/articles/PMC9660216/
- *Negative verbal probabilities undermine communication of climate science*, Nature Climate Change 2025.
  https://www.nature.com/articles/s41558-025-02472-1
