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
    # Regex of allowed origins (in addition to cors_origins). Defaults to any
    # Vercel deployment (prod + preview) and any maestroai.mx subdomain so the
    # portal connects from its custom domain too. Set to "" to disable.
    cors_origin_regex: str = r"https://(.*\.)?(vercel\.app|maestroai\.mx)"

    # Premium external (OpenAI / Claude / Gemini compatible)
    premium_enabled: bool = False
    premium_base_url: str = "https://api.openai.com/v1"
    premium_api_key: str = ""
    premium_model: str = "gpt-4o-mini"

    # Cost-optimized open-models / volume route — provider: NaN Builders.
    # OpenAI-compatible endpoint; set base_url + api_key when onboarded.
    open_enabled: bool = False
    open_provider_name: str = "NaN Builders"
    open_base_url: str = "https://api.nanbuilders.com/v1"
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

    # Embeddings / RAG. Provider: "local" | "open" (NaN Builders) | "premium".
    embeddings_provider: str = "local"
    embeddings_model: str = "text-embedding-3-small"
    embeddings_dim: int = 384

    # Vector store: "inprocess" (default) or "qdrant"
    vector_store: str = "inprocess"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # Workflows: n8n (blueprint §4/§9). Managed model — the platform provisions
    # each tenant's workflows so non-technical users configure nothing.
    n8n_enabled: bool = False
    n8n_webhook_base_url: str = ""  # managed webhook base, e.g. https://n8n.tu-saas.com/webhook
    n8n_api_key: str = ""           # n8n API key (webhook header auth + REST provisioning)
    n8n_auth_header: str = "X-N8N-API-KEY"
    # REST API of the managed n8n, used to auto-create tenant workflows.
    n8n_api_base_url: str = ""      # e.g. https://n8n.tu-saas.com/api/v1
    n8n_auto_provision: bool = True

    # In-process scheduler for time-based automations (or use /automations/run-due).
    scheduler_enabled: bool = False

    # Encryption at rest (KMS abstraction). master_kms_key seeds per-tenant keys.
    # In production this comes from a real KMS (AWS KMS, GCP KMS, Vault).
    encryption_enabled: bool = True
    master_kms_key: str = ""  # falls back to secret_key when empty
    kms_key_version: int = 1  # bump to rotate

    # Provider resilience: fallback order tried when a route's adapter fails.
    fallback_order: str = "vpc,open,local"

    # SSO / OIDC (optional, pluggable). When disabled, password login is used.
    sso_enabled: bool = False
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:3000/auth/callback"
    oidc_default_role: str = "user"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fallback_routes(self) -> list[str]:
        return [r.strip() for r in self.fallback_order.split(",") if r.strip()]

    @property
    def effective_kms_key(self) -> str:
        return self.master_kms_key or self.secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
