"""MacroPilot API - FastAPI-Einstiegspunkt."""

import asyncio
import contextlib
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import store
from .config import get_settings
from .explain import resolve_provider
from .refresh import scheduler
from .routers import dashboard, liquidity, ops

settings = get_settings()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Taeglicher Refresh im Hintergrund (D1), abschaltbar mit AUTO_REFRESH=false."""
    task = asyncio.create_task(scheduler()) if settings.auto_refresh else None
    try:
        yield
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = FastAPI(
    lifespan=lifespan,
    title="MacroPilot API",
    version="0.2.0",
    description=(
        "Makro-Daten fuer das MacroPilot-Dashboard. Saeule 1 (Liquiditaet, Net Liquidity mit "
        "Perzentil-plus-Momentum-Score) ist live, Saeulen 2 bis 4 sind Platzhalter."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(liquidity.router)
app.include_router(ops.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    provider = await resolve_provider()
    models = {
        "anthropic": settings.explain_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
        "template": "regelbasiert",
    }
    return {
        "status": "ok",
        "fred_api_key_configured": bool(settings.fred_api_key),
        "anthropic_api_key_configured": bool(settings.anthropic_api_key),
        "gemini_api_key_configured": bool(settings.gemini_api_key),
        "explain_provider": provider,
        "explain_model": models.get(provider),
        "cache_ttl_seconds": settings.cache_ttl_seconds,
        "last_refresh": store.get_meta("last_refresh"),
        "snapshot_date": store.get_meta("last_snapshot_date"),
        "auto_refresh": settings.auto_refresh,
        "alert_channels": [c for c in ("ntfy", "email") if (settings.ntfy_topic if c == "ntfy" else settings.smtp_host and settings.alert_email_to)],
        "oldest_input": store.get_meta("oldest_input"),
        "recording_since": store.first_snapshot_date(),
    }
