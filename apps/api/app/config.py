"""Centralized configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me-please-32-characters-min"
    access_token_expire_minutes: int = 720

    database_url: str = "sqlite:///./privateai.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Premium external (OpenAI / Claude / Gemini compatible)
    premium_enabled: bool = False
    premium_base_url: str = "https://api.openai.com/v1"
    premium_api_key: str = ""
    premium_model: str = "gpt-4o-mini"

    # Cost-optimized open model
    open_enabled: bool = False
    open_base_url: str = "https://openrouter.ai/api/v1"
    open_api_key: str = ""
    open_model: str = "meta-llama/llama-3.1-8b-instruct"

    # VPC private (vLLM / TGI)
    vpc_enabled: bool = False
    vpc_base_url: str = "http://vllm:8000/v1"
    vpc_api_key: str = ""
    vpc_model: str = "Qwen2.5-7B-Instruct"

    # Local self-hosted (Ollama)
    local_enabled: bool = False
    local_base_url: str = "http://localhost:11434/v1"
    local_model: str = "llama3.1"

    # Embeddings / RAG
    embeddings_provider: str = "local"
    embeddings_dim: int = 384

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
