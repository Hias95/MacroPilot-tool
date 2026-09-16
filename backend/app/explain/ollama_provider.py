"""Erklaerung ueber ein lokales Modell via Ollama (kostenlos, privat, laeuft auf der eigenen GPU).

Installation: https://ollama.com/download, danach z. B. `ollama pull gemma3:12b`.
Das Backend erkennt einen laufenden Ollama-Server automatisch.
"""

from __future__ import annotations

import time

import httpx

from ..config import get_settings
from ..schemas import PillarResponse
from .base import SYSTEM_PROMPT, GenResult, user_message

_availability: tuple[float, bool] = (0.0, False)
AVAILABILITY_TTL = 60.0


async def is_available() -> bool:
    """Prueft, ob der Ollama-Server antwortet. Ergebnis wird 60 Sekunden gemerkt."""
    global _availability
    checked_at, available = _availability
    if time.time() - checked_at < AVAILABILITY_TTL:
        return available
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            response = await client.get(f"{settings.ollama_host}/api/tags")
            available = response.status_code == 200
    except httpx.HTTPError:
        available = False
    _availability = (time.time(), available)
    return available


async def generate(p: PillarResponse) -> GenResult:
    settings = get_settings()
    model = settings.ollama_model
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message(p)},
        ],
        "options": {"temperature": 0.4, "num_predict": settings.explain_max_tokens},
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{settings.ollama_host}/api/chat", json=payload)
    except httpx.HTTPError as exc:
        return GenResult(None, model, f"Ollama nicht erreichbar: {type(exc).__name__}.")
    if response.status_code == 404:
        return GenResult(None, model, f"Modell {model} fehlt. Bitte `ollama pull {model}` ausführen.")
    if response.status_code != 200:
        return GenResult(None, model, f"Ollama antwortete mit {response.status_code}.")
    text = (response.json().get("message", {}).get("content") or "").strip()
    return GenResult(text or None, model, None if text else "Leere Antwort von Ollama.")
