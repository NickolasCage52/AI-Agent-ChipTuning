from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    core_api_url: str = "http://core-api:8000"
    agent_url: str = "http://agent-orchestrator:8001"

    telegram_bot_token: str | None = None
    telegram_webhook_secret: str = "devsecret"
    public_base_url: str | None = None


settings = Settings()

