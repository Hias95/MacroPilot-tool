"""Gemini- und Ollama-Provider mit Mocks: Aufbau der Anfrage und Auswertung der Antwort."""

from types import SimpleNamespace

import httpx

from app import config
from app.explain import gemini_provider, ollama_provider
from tests.test_explain import liquidity_fixture


async def test_gemini_provider_builds_config_and_reads_text(monkeypatch):
    settings = config.get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "g-key")
    captured = {}

    async def fake_generate(*, model, contents, config):
        captured.update(model=model, contents=contents, config=config)
        return SimpleNamespace(text="Die Industrie stabilisiert sich.")

    fake_client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate)))
    monkeypatch.setattr(gemini_provider, "_get_client", lambda: fake_client)

    result = await gemini_provider.generate(liquidity_fixture())

    assert result.text == "Die Industrie stabilisiert sich." and result.error is None
    assert captured["model"] == settings.gemini_model
    assert "Liquidität" in captured["contents"]
    assert captured["config"].system_instruction.startswith("Du schreibst für MacroPilot")
    assert captured["config"].thinking_config.thinking_budget == 0


async def test_gemini_without_key_reports_error():
    result = await gemini_provider.generate(liquidity_fixture())
    assert result.text is None and "Key" in result.error


async def test_ollama_provider_parses_chat_response(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.content
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "Lokal erklärt."}})

    real_client = httpx.AsyncClient

    def patched_client(**kwargs):
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(ollama_provider.httpx, "AsyncClient", patched_client)
    result = await ollama_provider.generate(liquidity_fixture())

    assert result.text == "Lokal erklärt." and result.error is None
    assert seen["url"].endswith("/api/chat") and "Liquidität".encode() in seen["body"]


async def test_ollama_missing_model_gives_pull_hint(monkeypatch):
    real_client = httpx.AsyncClient

    def patched_client(**kwargs):
        return real_client(transport=httpx.MockTransport(lambda r: httpx.Response(404, json={"error": "model not found"})), **kwargs)

    monkeypatch.setattr(ollama_provider.httpx, "AsyncClient", patched_client)
    result = await ollama_provider.generate(liquidity_fixture())
    assert result.text is None and "ollama pull" in result.error
