"""Erklaerung ueber die Anthropic Messages API (kostenpflichtig, pay-as-you-go)."""

from __future__ import annotations

import anthropic
from anthropic import AsyncAnthropic, DefaultAsyncHttpxClient

from ..config import get_settings
from ..schemas import PillarResponse
from .base import SYSTEM_PROMPT, GenResult, ssl_context, user_message

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        settings = get_settings()
        kwargs: dict = {"http_client": DefaultAsyncHttpxClient(verify=ssl_context()), "max_retries": 1, "timeout": 90.0}
        if settings.anthropic_api_key:
            kwargs["api_key"] = settings.anthropic_api_key
        _client = AsyncAnthropic(**kwargs)
    return _client


def _has_credentials(client: AsyncAnthropic) -> bool:
    return any(getattr(client, attr, None) for attr in ("api_key", "auth_token", "credentials"))


async def generate(p: PillarResponse) -> GenResult:
    settings = get_settings()
    model = settings.explain_model
    client = _get_client()
    if not _has_credentials(client):
        return GenResult(None, model, "Kein Anthropic-API-Key konfiguriert.")
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=settings.explain_max_tokens,
            system=SYSTEM_PROMPT,
            output_config={"effort": settings.explain_effort},
            messages=[{"role": "user", "content": user_message(p)}],
        )
    except (anthropic.AuthenticationError, anthropic.CredentialsError):
        return GenResult(None, model, "Anthropic-API-Key ungültig.")
    except anthropic.RateLimitError:
        return GenResult(None, model, "Rate-Limit der Anthropic-API erreicht.")
    except anthropic.APIStatusError as exc:
        return GenResult(None, model, f"Anthropic-API-Fehler {exc.status_code}.")
    except anthropic.APIConnectionError:
        return GenResult(None, model, "Anthropic-API nicht erreichbar.")
    except anthropic.AnthropicError as exc:
        return GenResult(None, model, f"Anthropic-SDK: {type(exc).__name__}.")

    if response.stop_reason == "refusal":
        return GenResult(None, model, "Das Modell hat die Anfrage abgelehnt.")
    text = "\n".join(block.text for block in response.content if block.type == "text").strip()
    return GenResult(text or None, response.model, None if text else "Leere Antwort vom Modell.")
