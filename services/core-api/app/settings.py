from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Used by Alembic (sync)
    database_url: str
    # Used by app runtime (async)
    async_database_url: str
    orchestrator_url: str = "http://agent-orchestrator:8001"
    rag_url: str = "http://rag-service:8003"
    log_level: str = "info"
    estimate_requires_approval: bool = True


settings = Settings()

