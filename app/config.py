from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("ENV", "dev")
    loop_send_url: str = os.getenv(
        "LOOP_SEND_URL", "https://server.loopmessage.com/api/v1/message/send/"
    )
    loop_authorization: str = os.getenv("LOOP_AUTHORIZATION", "")
    loop_secret_key: str = os.getenv("LOOP_SECRET_KEY", "")
    loop_sender_name: str = os.getenv("LOOP_SENDER_NAME", "")
    loop_webhook_auth: str | None = os.getenv("LOOP_WEBHOOK_AUTH")
    status_callback_url: str | None = os.getenv("STATUS_CALLBACK_URL")
    status_callback_auth: str | None = os.getenv("STATUS_CALLBACK_AUTH")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")


def get_settings() -> Settings:
    return Settings()

