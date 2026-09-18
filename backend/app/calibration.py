"""Trefferbilanz: Hat das Tool recht behalten?

Seit dem 18.09.2026 schreibt jeder Export fest, was an diesem Tag behauptet wurde (Meta-Schluessel
`outlook:<Datum>`). Sobald der Horizont von dreizehn Wochen verstrichen ist, laesst sich jede dieser
Aussagen gegen den tatsaechlichen Kursverlauf pruefen.

Der Vergleich ist bewusst schlicht: Behauptet wurde eine Wahrscheinlichkeit dafuer, dass der Index dreizehn
Wochen spaeter hoeher steht. Ueber viele Aussagen hinweg muss die durchschnittlich behauptete
Wahrscheinlichkeit ungefaehr der tatsaechlichen Trefferquote entsprechen. Weicht sie systematisch ab, ist
das Modell schlecht geeicht, unabhaengig davon, ob es im Einzelfall richtig lag.

Aufruf:  python -m app.calibration
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta

from . import market, store
from .backtest import PriceIndex, forward_return

HORIZON_WEEKS = 13


def logged() -> list[dict]:
    """Alle protokollierten Erwartungen, aelteste zuerst."""
    out = []
    for key, raw in store.meta_with_prefix("outlook:").items():
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        entry.setdefault("stated_on", key.removeprefix("outlook:"))
        out.append(entry)
    return sorted(out, key=lambda e: e["stated_on"])


async def evaluate(today: date | None = None) -> dict:
    """Bilanz ueber alle Aussagen, deren Horizont verstrichen ist."""
    today = today or date.today()
    entries = logged()
    if not entries:
        return {"logged": 0, "matured": 0, "hits": 0, "stated_avg": None, "actual_rate": None, "due_from": None}

    due_from = (date.fromisoformat(entries[0]["stated_on"]) + timedelta(weeks=HORIZON_WEEKS)).isoformat()
    mature = [e for e in entries
              if date.fromisoformat(e["stated_on"]) + timedelta(weeks=HORIZON_WEEKS) <= today]
    if not mature:
        return {"logged": len(entries), "matured": 0, "hits": 0, "stated_avg": None,
                "actual_rate": None, "due_from": due_from}

    (spy, _) = await market.fetch_weekly_closes("SPY")
    prices = PriceIndex(spy.observations)
    hits, checked, stated = 0, 0, []
    for e in mature:
        ret = forward_return(prices, date.fromisoformat(e["stated_on"]), HORIZON_WEEKS)
        if ret is None:
            continue
        checked += 1
        stated.append(e.get("hit_rate_13w") or 0.0)
        if ret > 0:
            hits += 1
    return {
        "logged": len(entries), "matured": checked, "hits": hits, "due_from": due_from,
        "stated_avg": round(sum(stated) / len(stated), 1) if stated else None,
        "actual_rate": round(100 * hits / checked, 1) if checked else None,
    }


async def main() -> None:
    result = await evaluate()
    print(f"Protokolliert: {result['logged']} Aussagen")
    if not result["matured"]:
        print(f"Noch keine ausgewertet. Erste Auswertung moeglich ab {result['due_from']}.")
        return
    print(f"Ausgewertet: {result['matured']} | davon eingetroffen: {result['hits']}")
    print(f"Behauptet im Schnitt {result['stated_avg']} %, tatsaechlich {result['actual_rate']} %")


if __name__ == "__main__":
    asyncio.run(main())
