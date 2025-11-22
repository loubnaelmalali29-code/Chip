"""Configuration management for Chip following OpenPoke patterns."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load .env from root directory if present."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                key, value = key.strip(), value.strip().strip("'\"")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


_load_env_file()


DEFAULT_APP_NAME = "Chip - Alabama Tech Community AI Agent"
DEFAULT_APP_VERSION = "0.1.0"


def _env_int(name: str, fallback: int) -> int:
    try:
        return int(os.getenv(name, str(fallback)))
    except (TypeError, ValueError):
        return fallback


class Settings(BaseModel):
    """Application settings with all required environment variables for Chip."""

    # App metadata
    app_name: str = Field(default=DEFAULT_APP_NAME)
    app_version: str = Field(default=DEFAULT_APP_VERSION)

    # Server runtime
    server_host: str = Field(default=os.getenv("CHIP_HOST", "0.0.0.0"))
    server_port: int = Field(default=_env_int("CHIP_PORT", 8000))

    # Environment
    env: str = Field(default=os.getenv("ENV", "dev"))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))

    # HTTP behaviour
    cors_allow_origins_raw: str = Field(default=os.getenv("CORS_ORIGINS", "*"))
    enable_docs: bool = Field(default=os.getenv("CHIP_ENABLE_DOCS", "1") != "0")
    docs_url: Optional[str] = Field(default=os.getenv("DOCS_URL", "/docs"))

    # Google Gemini support (from Google AI Studio)
    google_api_key: Optional[str] = Field(default=os.getenv("GOOGLE_API_KEY"))
    gemini_api_key: Optional[str] = Field(default=os.getenv("GEMINI_API_KEY"))
    gemini_model: str = Field(default=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    # Legacy Groq support
    groq_api_key: Optional[str] = Field(default=os.getenv("GROQ_API_KEY"))
    groq_model: str = Field(default=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"))

    # Hume AI configuration
    hume_api_key: Optional[str] = Field(default=os.getenv("HUME_API_KEY"))

    # Supabase configuration
    supabase_url: Optional[str] = Field(default=os.getenv("SUPABASE_URL"))
    supabase_anon_key: Optional[str] = Field(default=os.getenv("SUPABASE_ANON_KEY"))
    supabase_service_role_key: Optional[str] = Field(default=os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    # Legacy Supabase key support
    supabase_key: Optional[str] = Field(default=os.getenv("SUPABASE_KEY"))

    # Twilio configuration
    twilio_account_sid: Optional[str] = Field(default=os.getenv("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: Optional[str] = Field(default=os.getenv("TWILIO_AUTH_TOKEN"))
    twilio_from_number: Optional[str] = Field(default=os.getenv("TWILIO_FROM_NUMBER"))
    twilio_webhook_secret: Optional[str] = Field(default=os.getenv("TWILIO_WEBHOOK_SECRET"))

    # Loop Messaging configuration
    loop_api_key: Optional[str] = Field(default=os.getenv("LOOP_API_KEY"))
    loop_webhook_secret: Optional[str] = Field(default=os.getenv("LOOP_WEBHOOK_SECRET"))
    loop_send_url: str = Field(
        default=os.getenv("LOOP_SEND_URL", "https://server.loopmessage.com/api/v1/message/send/")
    )
    loop_authorization: str = Field(default=os.getenv("LOOP_AUTHORIZATION", ""))
    loop_secret_key: str = Field(default=os.getenv("LOOP_SECRET_KEY", ""))
    loop_sender_name: str = Field(default=os.getenv("LOOP_SENDER_NAME", ""))
    loop_webhook_auth: Optional[str] = Field(default=os.getenv("LOOP_WEBHOOK_AUTH"))
    status_callback_url: Optional[str] = Field(default=os.getenv("STATUS_CALLBACK_URL"))
    status_callback_auth: Optional[str] = Field(default=os.getenv("STATUS_CALLBACK_AUTH"))

    # Temporal configuration
    temporal_host: Optional[str] = Field(default=os.getenv("TEMPORAL_HOST"))
    temporal_namespace: Optional[str] = Field(default=os.getenv("TEMPORAL_NAMESPACE", "default"))

    @property
    def cors_allow_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if self.cors_allow_origins_raw.strip() in {"", "*"}:
            return ["*"]
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]

    @property
    def resolved_docs_url(self) -> Optional[str]:
        """Return documentation URL when docs are enabled."""
        return (self.docs_url or "/docs") if self.enable_docs else None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


