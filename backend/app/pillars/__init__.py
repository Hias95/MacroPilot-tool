"""Registry der Saeulen: drei Treiber und drei Overlays. Jede Saeule liefert eine PillarResponse."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from ..schemas import PillarId, PillarResponse
from . import cycle, liquidity, markets, mechanics, structure, valuation

PROVIDERS: dict[str, Callable[[], Awaitable[PillarResponse]]] = {
    "liquidity": liquidity.build,
    "cycle": cycle.build,
    "markets": markets.build,
    "structure": structure.build,
    "mechanics": mechanics.build,
    "valuation": valuation.build,
}

ORDER: list[PillarId] = ["liquidity", "cycle", "structure"]
OVERLAYS: list[PillarId] = ["valuation", "mechanics", "markets"]


async def get_pillar(pillar_id: PillarId) -> PillarResponse:
    return await PROVIDERS[pillar_id]()


async def get_all() -> list[PillarResponse]:
    return list(await asyncio.gather(*(PROVIDERS[p]() for p in ORDER)))


async def get_overlays() -> list[PillarResponse]:
    return list(await asyncio.gather(*(PROVIDERS[p]() for p in OVERLAYS)))
