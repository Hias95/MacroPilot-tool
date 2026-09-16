"""Erklaerungen pro Saeule: Provider-Auswahl, Cache pro Daten-Fingerprint, Fallback auf regelbasiert.

Provider (EXPLAIN_PROVIDER):
  auto      -> anthropic wenn Key, sonst gemini wenn Key, sonst ollama wenn erreichbar, sonst template
  template  -> regelbasiert, immer kostenlos, keine externe Abhaengigkeit
  ollama    -> lokales Modell, kostenlos
  gemini    -> Google Gemini API
  anthropic -> Claude API (kostenpflichtig)
  none      -> keine Erklaerungen
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from ..config import get_settings
from ..schemas import ExplanationResponse, PillarResponse
from . import anthropic_provider, gemini_provider, ollama_provider, template

PROVIDERS = {
    "anthropic": anthropic_provider,
    "gemini": gemini_provider,
    "ollama": ollama_provider,
    "template": template,
}

# key -> (gespeichert_um, antwort, war_fallback)
_cache: dict[str, tuple[float, ExplanationResponse, bool]] = {}
_locks: dict[str, asyncio.Lock] = {}


def clear_cache() -> None:
    _cache.clear()


async def resolve_provider() -> str:
    settings = get_settings()
    choice = settings.explain_provider.strip().lower()
    if choice in PROVIDERS or choice == "none":
        return choice
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.gemini_api_key:
        return "gemini"
    if await ollama_provider.is_available():
        return "ollama"
    return "template"


def _fresh(entry: tuple[float, ExplanationResponse, bool] | None) -> ExplanationResponse | None:
    if entry is None:
        return None
    stored_at, result, was_fallback = entry
    if not was_fallback or time.time() - stored_at < get_settings().explain_error_ttl_seconds:
        return result.model_copy(update={"cached": True})
    return None


async def _generate(p: PillarResponse, provider: str) -> tuple[ExplanationResponse, bool]:
    now = datetime.now(tz=timezone.utc)
    result = await PROVIDERS[provider].generate(p)
    if result.text:
        response = ExplanationResponse(
            pillar_id=p.id, status="ready", text=result.text, provider=provider,  # type: ignore[arg-type]
            model=result.model, generated_at=now, fingerprint=p.fingerprint,
        )
        return response, False
    # KI nicht verfuegbar: regelbasiert einspringen lassen, Grund mitgeben.
    fallback = await template.generate(p)
    response = ExplanationResponse(
        pillar_id=p.id, status="ready", text=fallback.text, provider="template", model=fallback.model,
        reason=f"{provider}: {result.error}", generated_at=now, fingerprint=p.fingerprint,
    )
    return response, True


async def explain_pillar(p: PillarResponse) -> ExplanationResponse:
    provider = await resolve_provider()
    if provider == "none":
        return ExplanationResponse(
            pillar_id=p.id, status="unavailable", fingerprint=p.fingerprint,
            reason="Erklärungen sind deaktiviert (EXPLAIN_PROVIDER=none).",
        )
    key = f"{p.id}:{p.fingerprint}:{provider}"
    if (hit := _fresh(_cache.get(key))) is not None:
        return hit
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        if (hit := _fresh(_cache.get(key))) is not None:
            return hit
        result, was_fallback = await _generate(p, provider)
        _cache[key] = (time.time(), result, was_fallback)
        return result
