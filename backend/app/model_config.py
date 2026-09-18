"""Alle Modellparameter an einem Ort, damit Backtest und Kalibrierung sie gezielt veraendern koennen.

Score je Teilindikator = level_weight * Niveau-Perzentil + (1 - level_weight) * Momentum-Perzentil.
lookback und momentum_window zaehlen in Beobachtungen der jeweiligen Frequenz (Wochen oder Monate).
change_mode: "pct" fuer Geldmengen und Verhaeltnisse, "abs" fuer Indizes, Zinsen und Raten um null.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreParams:
    momentum_window: int
    level_weight: float
    lookback: int
    change_mode: str
    min_history: int
    unit: str = "weeks"

    def series_kwargs(self) -> dict:
        """Argumente fuer scoring.score_series (Endpunkt einer Serie)."""
        return {
            "momentum_window": self.momentum_window, "level_weight": self.level_weight,
            "lookback": self.lookback, "change_mode": self.change_mode, "unit": self.unit,
        }

    def history_kwargs(self) -> dict:
        """Argumente fuer scoring.score_history (ganze Zeitreihe)."""
        return {
            "momentum_window": self.momentum_window, "level_weight": self.level_weight,
            "lookback": self.lookback, "change_mode": self.change_mode, "min_history": self.min_history,
        }


# Saeule 1: Net Liquidity, woechentlich. 10 Jahre Niveau, 26 Wochen Momentum (C2: 26 statt 13 Wochen, weil
# Liquiditaet langsam wirkt; Lernfenster IC +0,28 statt +0,22, und der Score wird ruhiger).
LIQUIDITY = ScoreParams(momentum_window=26, level_weight=0.4, lookback=520, change_mode="pct", min_history=104)

# Saeule 1, Zusatzsignale: globaler Notenbank-Proxy (Fed + EZB + BoJ in USD, woechentlich) und
# T-Bill-Anteil an den Staatsschulden (monatlich, Momentum in Prozentpunkten, 6 Monate = 26 Wochen).
LIQUIDITY_GLOBAL = ScoreParams(momentum_window=26, level_weight=0.4, lookback=520, change_mode="pct", min_history=104)
LIQUIDITY_TBILL = ScoreParams(momentum_window=6, level_weight=0.4, lookback=120, change_mode="abs", min_history=36, unit="months")
LIQUIDITY_WEIGHTS = {"net": 0.5, "global": 0.3, "tbill": 0.2}

# Saeule 2: Regional-Fed-Composite, monatlich, schwankt um null.
CYCLE = ScoreParams(momentum_window=3, level_weight=0.4, lookback=120, change_mode="abs", min_history=36, unit="months")

# Saeule 3: Marktsignale, woechentlich. 5 Jahre Niveau, weil Verhaeltnisse wie RSP/SPY jahrzehntelange
# Trends haben und ein 10-Jahres-Perzentil die Breite dauerhaft "niedrig" nennen wuerde.
MARKETS = ScoreParams(momentum_window=13, level_weight=0.4, lookback=260, change_mode="pct", min_history=104)

# Saeule 4: Zinsen und Inflation als Niveaus in Prozent(punkten): Momentum absolut.
STRUCTURE_WEEKLY = ScoreParams(momentum_window=13, level_weight=0.4, lookback=520, change_mode="abs", min_history=104)
STRUCTURE_MONTHLY = ScoreParams(momentum_window=3, level_weight=0.4, lookback=120, change_mode="abs", min_history=36, unit="months")
STRUCTURE_QUARTERLY = ScoreParams(momentum_window=2, level_weight=0.4, lookback=40, change_mode="abs", min_history=12, unit="quarters")

# Gewichte der Bestandteile von Struktur & Fiskus (Summe 1.0).
STRUCTURE_WEIGHTS = {"curve": 0.30, "real": 0.25, "cpi": 0.15, "dsr": 0.15, "interest": 0.15}

# Un-Inversion: Versteilung nach einer Inversion ist das eigentliche Krisensignal.
# War die Kurve in den letzten lookback_weeks invers und stieg sie in steepening_weeks um mehr als
# min_rise_pp, wird der Kurven-Score auf cap gedeckelt.
UNINVERSION = {"lookback_weeks": 52, "steepening_weeks": 13, "min_rise_pp": 0.5, "cap": 40}

# Regime-Flag Fiskalische Dominanz: aktiv, wenn `needed` von drei Kriterien zutreffen.
FISCAL_FLAG = {"interest_tax_pct": 25.0, "tbill_share_pct": 20.0, "repression_pp": 0.0, "needed": 2}

# Veroeffentlichungsverzug in Tagen: Daten werden im Verlauf erst ab Publikation sichtbar (kein Look-ahead).
# C3 (16.09.2026): regional_fed = Umfragen erscheinen ab Mitte des Monats, Dallas am letzten Montag, deshalb 30 Tage
# ab Monatsanfang; mspd = Treasury-Schuldenstand am 5. Geschaeftstag des Folgemonats; boj = BoJ-Bilanz zum Monatsende,
# auf FRED zum Monatsanfang datiert, veroeffentlicht Anfang des Folgemonats.
PUBLICATION_LAG_DAYS = {"cpi": 45, "dsr": 170, "bea_quarterly": 120, "regional_fed": 30, "mspd": 7, "boj": 35}

# Overlay Marktmechanik / Volatilitaet: VIX-Niveau, Terminstruktur VIX/VIX3M, SKEW. Alle invertiert (hoch = Stress).
MECHANICS_LEVEL = ScoreParams(momentum_window=13, level_weight=0.4, lookback=520, change_mode="abs", min_history=104)
MECHANICS_RATIO = ScoreParams(momentum_window=13, level_weight=0.4, lookback=520, change_mode="pct", min_history=104)
MECHANICS_WEIGHTS = {"vix": 0.4, "term": 0.4, "skew": 0.2}
# Kontra-Regel: VIX-Niveau im obersten Zehntel der letzten zehn Jahre = Panik-Zone (historisch eher Kaufzone).
PANIC_VIX_PERCENTILE = 90

# Overlay Bewertung / Fallhoehe: Bewertung ist Fallhoehe, kein Timing, deshalb 80 % Niveau ueber 30 Jahre.
VALUATION_MONTHLY = ScoreParams(momentum_window=3, level_weight=0.8, lookback=360, change_mode="pct", min_history=120, unit="months")
VALUATION_MONTHLY_ABS = ScoreParams(momentum_window=3, level_weight=0.8, lookback=360, change_mode="abs", min_history=120, unit="months")
VALUATION_QUARTERLY = ScoreParams(momentum_window=2, level_weight=0.8, lookback=120, change_mode="pct", min_history=40, unit="quarters")
VALUATION_WEIGHTS = {"cape": 0.4, "ecy": 0.4, "buffett": 0.2}
# Regime-Flag Extreme Bewertung: zwei von drei: CAPE im obersten Zehntel (30 J), Risikopraemie unter 1 %,
# Buffett-Indikator im obersten Zehntel (30 J).
VALUATION_FLAG = {"cape_percentile": 90, "ecy_min_pct": 1.0, "buffett_percentile": 90, "needed": 2}
# Fallhoehe-Label nach Overlay-Score
VALUATION_LABELS = [(70, "günstig"), (45, "fair"), (25, "teuer"), (0, "extrem teuer")]
PUBLICATION_LAG_DAYS["shiller"] = 35      # Monatsdaten, Datei erscheint im Folgemonat
PUBLICATION_LAG_DAYS["z1_quarterly"] = 160  # Fed-Finanzierungsrechnung, gut zwei Monate nach Quartalsende

# ---------------------------------------------------------------------------------------------
# Consensus v2. Kern = gewichtete Treiber. Marktmechanik korrigiert um bis zu |MECHANICS_RANGE| Punkte.
# Bewertung deckelt nach oben: Deckel = base + slope * Bewertungs-Score (0 -> 60, 100 -> 100).
# Vetos deckeln bei Systemkrisen.
# Kalibrierung C2 (16.09.2026, Walk-Forward: 2011-2018 lernen, 2019-2026 pruefen, docs/backtest-c2.md):
# Liquiditaet traegt am meisten, Struktur mehr als Konjunktur. Marktsignale sind seit dem 16.09.2026 kein
# Treiber mehr (docs/marktsignale-rolle.md): ihr Niveau ist ein Kontra-Signal, ihr Momentum kaum informativ;
# sie wirken als Overlay "Marktbestaetigung" (Bestaetigung/Divergenz zum Makro-Kern, Flag Marktstress).
# Drei Treiber, Lernfenster IC +0,29, Pruef-Fenster +0,39. Alte Gewichte 35/25/25/15, dann 50/10/15/25.
# ---------------------------------------------------------------------------------------------
# Gewichte der Treiber. Bis 18.09.2026 lagen sie bei 55/15/30 aus der Walk-Forward-Kalibrierung (C2).
# Die Untersuchung in docs/liquiditaet-wirklich-55.md zeigte, dass diese Konzentration nicht gedeckt ist:
# Struktur & Fiskus sagt ueber den ganzen Zeitraum mindestens so viel vorher wie die Liquiditaet (+0,15 gegen
# +0,10 auf 13 Wochen), und die scheinbar klaren Umfeld-Unterschiede drehen zwischen den Zeithaelften das
# Vorzeichen. Der Grund fuer die ausgewogenere Verteilung ist deshalb nicht ein besserer Messwert, sondern
# Vorsicht: Wenn nicht zuverlaessig feststeht, welcher Treiber fuehrt, wird das Gewicht nicht auf einen
# konzentriert. Die Konjunktur behaelt ihre 15 Prozent, obwohl sie fuer sich genommen nichts liefert, weil die
# Zyklusphase aus Liquiditaets- und Konjunkturrichtung entsteht.
CONSENSUS_WEIGHTS = {"liquidity": 0.40, "cycle": 0.15, "structure": 0.45}
# Overlay Marktbestaetigung: Marktsignal-Score gegen den Consensus-Rang (beide ueber/unter der Schwelle =
# bestaetigt). Markt hoch bei Makro tief war historisch die schwaechste Kombination (13 W +1,8 %, 66 % Treffer),
# Makro hoch bei Markt tief bringt gleiche Rendite, aber mehr Rueckschlaege (P10 -4,3 % statt +1,3 %).
MARKET_CONFIRM_THRESHOLD = 50
# Regime-Flag Marktstress: Marktsignal-Score unter stress_below (12 % der Wochen, halbe Aktienquote halbierte
# historisch den Drawdown); unter capitulation_below Kapitulation (5 % der Wochen, 13 W danach +10 %, 95 % Treffer).
MARKET_STRESS = {"stress_below": 30, "capitulation_below": 20}
# Negativ = Kontra: Stress (niedriger Mechanik-Score) hebt den Rohwert um bis zu 5 Punkte, Sorglosigkeit senkt
# ihn. C2: mit +5 (Stress senkt) war der IC in Lern- und Pruef-Fenster durchgehend schlechter als mit -5.
MECHANICS_RANGE = -5.0
VALUATION_CAP = {"base": 60.0, "slope": 0.4}
VETOES = {
    "liquidity_below": 20, "liquidity_cap": 35,
    "structure_below": 20, "structure_cap": 30,
    "mechanics_below": 30, "valuation_mechanics_cap": 40,   # nur zusammen mit aktivem Regime Extreme Bewertung
}
# Consensus-Rang (Entscheidung 16.09.2026, Backtest C1): Der Rohwert (gewichtetes Mittel) ist komprimiert und
# schwach. Gezeigt wird deshalb sein Perzentil gegenueber den letzten RANK_WINDOW_WEEKS Wochen:
# "besser als X % der Wochen der letzten zehn Jahre". Zonen sind Quantile des Rangs mit Ampelstufen.
RANK_WINDOW_WEEKS = 520
RANK_MIN_HISTORY = 104
ZONE_BANDS = [(10, "very_negative", "Stark negativ"), (30, "negative", "Negativ"), (70, "neutral", "Neutral"),
              (90, "positive", "Positiv"), (101, "very_positive", "Stark positiv")]
# Die Zone wechselt erst nach ZONE_CONFIRM_WEEKS Wochen in Folge (Zahl bleibt roh, Label wird ruhig).
ZONE_CONFIRM_WEEKS = 3
# Zyklusphase aus Richtung Liquiditaet x Richtung Konjunktur (Investment Clock), bestaetigt nach N Wochen.
PHASE_MATRIX = {("up", "down"): ("recovery", "Erholung"), ("up", "up"): ("expansion", "Aufschwung"),
                ("down", "up"): ("late", "Spätzyklus"), ("down", "down"): ("downturn", "Abschwung")}
PHASE_CONFIRM_WEEKS = 4
