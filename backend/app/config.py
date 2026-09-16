"""Zentrale Konfiguration. Werte kommen aus Umgebungsvariablen oder backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    fred_api_key: str | None = None
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cache_ttl_seconds: int = 3600
    # Persistenz (D1): SQLite unter data_dir. Rohdaten von der Platte gelten disk_cache_ttl_seconds lang als frisch;
    # scheitert das Netz, dienen sie unabhaengig vom Alter als Rueckfall.
    data_dir: str | None = None
    disk_cache_ttl_seconds: int = 20 * 3600
    # Taeglicher Refresh im Hintergrund (lokale Uhrzeit) und Token fuer POST /api/v1/refresh (leer = ohne Token).
    auto_refresh: bool = True
    refresh_hour: int = 7
    refresh_minute: int = 30
    refresh_token: str | None = None
    # Hinweise bei Regimewechsel (D3): ntfy.sh (kostenlos, ohne Konto) und/oder E-Mail per SMTP.
    ntfy_topic: str | None = None
    ntfy_server: str = "https://ntfy.sh"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    alert_email_from: str | None = None
    alert_email_to: str | None = None
    # Volle Historie fuer Score-Zeitreihen und Backtest (WALCL beginnt Ende 2002).
    fred_history_weeks: int = 1340
    history_start_year: int = 2003

    # Erklaerungen: auto | template | ollama | gemini | anthropic | none (siehe app/explain/__init__.py)
    explain_provider: str = "auto"
    explain_max_tokens: int = 700
    # Anthropic (kostenpflichtig)
    anthropic_api_key: str | None = None
    explain_model: str = "claude-opus-5"
    explain_effort: str = "medium"
    # Google Gemini (Gratis-Kontingent nur fuer Eigengebrauch im EWR)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    # Ollama, lokales Modell (kostenlos)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"
    # Fehlgeschlagene Erklaerungen werden kurz gecacht, damit ein Reload die API nicht hammert.
    explain_error_ttl_seconds: int = 300

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir) if self.data_dir else Path(__file__).resolve().parent.parent / "data"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
