from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    core_api_url: str = "http://core-api:8000"
    model_server_url: str = "http://model-server:8002"
    rag_url: str = "http://rag-service:8003"
    log_level: str = "info"
    use_model_nlu: bool = False
    require_approval: bool = True


settings = Settings()

