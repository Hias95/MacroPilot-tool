"""Erklaerung ueber die Google Gemini API (google-genai SDK).

Hinweis: Google erlaubt das kostenlose Kontingent im EWR, in der Schweiz und in UK nur fuer den
Eigengebrauch. Sobald die App anderen Nutzern dort angeboten wird, verlangt Google die bezahlte Stufe.
"""

from __future__ import annotations

import logging

from google import genai
from google.genai import errors, types

from ..config import get_settings
from ..schemas import PillarResponse
from .base import SYSTEM_PROMPT, GenResult, ssl_context, user_message

log = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        verify = ssl_context()
        _client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                timeout=90_000,
                client_args={"verify": verify},
                async_client_args={"verify": verify},
            ),
        )
    return _client


# Ein 404 auf generateContent heisst fast immer: Diesen Modellnamen gibt es fuer diesen Schluessel oder
# diese API-Version nicht mehr. Statt den Tageslauf still auf regelbasierte Texte zurueckfallen zu lassen,
# sucht der Client einmal ein verfuegbares Modell und merkt es sich fuer den Rest des Laufs.
_resolved_model: str | None = None
_MODEL_PREFERENCE = ("flash-lite", "flash", "pro")


def _pick_model(names: list[str]) -> str | None:
    """Bevorzugt kleine, schnelle Modelle; sie reichen fuer drei Saetze Erklaerung."""
    for token in _MODEL_PREFERENCE:
        for name in names:
            if token in name:
                return name.removeprefix("models/")
    return names[0].removeprefix("models/") if names else None


async def _discover_model() -> str | None:
    try:
        models = await _get_client().aio.models.list()
        names = [m.name for m in models if m.name and "generateContent" in (m.supported_actions or [])]
    except Exception as exc:  # noqa: BLE001 - die Suche darf den Lauf nicht stoppen
        log.warning("Gemini: Modellsuche fehlgeschlagen: %s", type(exc).__name__)
        return None
    picked = _pick_model(names)
    if picked:
        log.warning("Gemini: konfiguriertes Modell nicht verfuegbar, weiche auf %s aus", picked)
    return picked


async def generate(p: PillarResponse) -> GenResult:
    global _resolved_model
    settings = get_settings()
    model = _resolved_model or settings.gemini_model
    if not settings.gemini_api_key:
        return GenResult(None, model, "Kein Gemini-API-Key konfiguriert.")
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        max_output_tokens=settings.explain_max_tokens,
        temperature=0.4,
    )
    if model.startswith("gemini-2.5-flash"):
        # Denk-Tokens zaehlen zum Output-Limit; fuer kurze Erklaerungen abschalten.
        config.thinking_config = types.ThinkingConfig(thinking_budget=0)
    try:
        response = await _get_client().aio.models.generate_content(model=model, contents=user_message(p), config=config)
    except errors.APIError as exc:
        if exc.code == 429:
            return GenResult(None, model, "Gemini-Kontingent erschöpft (429). Später erneut versuchen.")
        if exc.code in (400, 401, 403):
            return GenResult(None, model, f"Gemini lehnt den Key ab ({exc.code}).")
        if exc.code == 404:
            if _resolved_model is None:
                found = await _discover_model()
                if found and found != model:
                    _resolved_model = found
                    return await generate(p)
            return GenResult(None, model, f"Gemini kennt das Modell '{model}' nicht (404). Namen in GEMINI_MODEL prüfen.")
        return GenResult(None, model, f"Gemini-API-Fehler {exc.code}.")
    except Exception as exc:  # Netzwerk- oder Zertifikatsfehler aus httpx
        return GenResult(None, model, f"Gemini nicht erreichbar: {type(exc).__name__}.")
    text = (response.text or "").strip()
    return GenResult(text or None, model, None if text else "Leere Antwort von Gemini.")
