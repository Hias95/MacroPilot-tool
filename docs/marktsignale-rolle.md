# Marktsignale: welche Rolle traegt Information? (16.09.2026)

Rohdaten: `docs/marktsignale-analyse-raw.txt` (Skript `python -m app.research_markets` in `backend/`).
Anlass: In C2 zeigte sich, dass die Saeule Marktsignale (Breite RSP/SPY, Risikoappetit AUD/JPY, Kupfer/Gold,
Kredit HYG/IEF) als Treiber Vorhersagekraft kostet. Frage: andere Rolle statt streichen?

## Befunde

1. **Das Niveau ist ein Kontra-Signal, das Momentum kaum informativ.** Nur-Niveau (5 Jahre) hat IC -0,23 auf 13
   Wochen (Kupfer/Gold sogar -0,54 auf 52 Wochen): hoch im Vergleich zu den letzten Jahren heisst spaeter
   schwaechere Renditen. Nur-Momentum 13 Wochen liegt bei +0,04, allein die Breite bei +0,15. Laengere Fenster
   verlieren auch das. Ein Treiber, der so zusammengesetzt ist, kann nichts beitragen.
2. **Bestaetigung zaehlt, nicht Richtung.** Makro-Kern (Liquiditaet, Konjunktur, Struktur) und Marktsignale in
   Quadranten, 13-Wochen-Rendite:
   - Makro hoch, Markt hoch: +5,9 %, 94 % Treffer, schlechteste zehn Prozent +1,3 %, Drawdown im Mittel -1,3 %.
   - Makro hoch, Markt tief: +5,9 %, 84 % Treffer, schlechteste zehn Prozent -4,3 %, 8 % der Faelle unter -10 %.
   - Makro tief, Markt hoch: +1,8 %, 66 % Treffer. Die schwaechste Kombination: Kurse laufen den Daten davon.
   - Makro tief, Markt tief: +2,7 %, 73 % Treffer.
   Der Markt aendert also nicht die erwartete Rendite des Makrobilds, sondern das Risiko darum herum.
3. **Extreme kippen.** Marktsignal-Score unter 20 (5 % der Wochen, 10 Episoden): danach +10,5 % in 13 Wochen,
   95 % Treffer. Unter 15: +13,3 %, 100 %. Ausverkauf war Wendepunkt, wie die Panik-Zone der Marktmechanik.
4. **Als Warnsignal wirkt der Score in der Strategie.** Makro-Kern-Zonen mit Basisquoten, dazu die Regel "Score
   unter 30: halbe Quote": Drawdown -15,9 % statt -29,0 %, Sharpe 0,94 statt 0,90, Rendite 11,9 % statt 13,2 %.
   Unter 30 sind 12,5 % der Wochen, 19 Episoden in 15 Jahren, im Mittel fuenf Wochen. Wer bei Kapitulation (unter
   20) wieder voll geht, gibt den Drawdown-Schutz fast ganz zurueck (-27,6 %): der Tiefpunkt liegt oft noch Wochen
   voraus. Kredit-Sorglosigkeit (Kredit-Score ueber 80) hat als Regel keinen Effekt.
5. **Drei Treiber statt vier.** Ohne Marktsignale ist der Kern nicht schlechter: Gewichte 55/15/30 (Liquiditaet,
   Konjunktur, Struktur) geben im Lernfenster IC +0,29 (vorher +0,27) und im Pruef-Fenster +0,39 (vorher +0,36).
   Die Historie wird laenger, weil der Kern nicht mehr auf HYG (ab 2007) wartet.

## Entscheidung

Marktsignale werden vom Treiber zum dritten Overlay **Marktbestaetigung**:

- Gewicht im Consensus 0. Der Kern besteht aus Liquiditaet 55 %, Konjunktur 15 %, Struktur & Fiskus 30 %.
- **Bestaetigung**: Marktsignal-Score und Consensus-Rang beide ueber oder beide unter 50 = "Markt bestaetigt".
  Rang hoch, Markt tief = "Markt zoegert" (Rendite gleich, Rueckschlaege haeufiger). Rang tief, Markt hoch =
  "Markt laeuft voraus" (schwaechste Kombination). Als Badge am Consensus und als Satz im Warum-Text.
- **Regime-Flag Marktstress**: Score unter 30 (Rueckschlaege verstaerken sich, historisch halbe Quote = halber
  Drawdown), unter 20 **Kapitulation** (Ausverkauf weit fortgeschritten, historisch 95 % positive Quartale, Tiefpunkt
  oft noch Wochen voraus). Beides sind Stufen eines Flags, sichtbar als Badge, in der Kachel und im Easy-Modus.
- Keine Punkte-Korrektur am Rohwert: die Zahl bleibt das Makrobild, der Markt qualifiziert das Risiko.

Parameter: `CONSENSUS_WEIGHTS`, `MARKET_CONFIRM_THRESHOLD`, `MARKET_STRESS` in `backend/app/model_config.py`.
Logik: `consensus.market_confirmation()`, `pillars/markets.stress_flag()`.

## Was das fuer den Nutzer heisst

Die Saeule bleibt sichtbar und erklaert, verliert aber ihre Stimme im Score. Dafuer beantwortet sie eine Frage, die
der Score nicht beantworten kann: Wie riskant ist die aktuelle Einordnung? Bestaetigt der Markt, ist die
Trefferquote am hoechsten. Zoegert er, sind Rueckschlaege wahrscheinlicher. Laeuft er voraus, ist Vorsicht
angebracht. Und in Stress und Kapitulation liefert sie die Warnung beziehungsweise den Hinweis auf den Wendepunkt.
