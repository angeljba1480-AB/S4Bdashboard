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
    open_base_url: str = "https://api.nan.builders/v1"
    open_api_key: str = ""
    open_model: str = "qwen3.6"
    # Modelo de imagen del proveedor abierto (NaN: flux-2-klein, requiere tier
    # inference). Es distinto del modelo de chat (open_model) — no se reutiliza.
    image_model: str = "flux-2-klein"

    # VPC private (vLLM / TGI)
    vpc_enabled: bool = False
    vpc_base_url: str = "http://vllm:8000/v1"
    vpc_api_key: str = ""
    vpc_model: str = "Qwen2.5-7B-Instruct"

    # Local self-hosted (Ollama)
    local_enabled: bool = False
    local_base_url: str = "http://localhost:11434/v1"
    local_model: str = "llama3.1"

    # HTTP timeout (seconds) for model providers. Cloud routes (open/premium) are
    # fast; self-hosted routes (local Ollama / VPC) run on CPU/GPU that must load
    # the model then generate, so they get a much longer default to avoid a
    # premature timeout falling back to a less-private cloud route.
    model_request_timeout: int = 120
    local_request_timeout: int = 300

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

    # Ingesta segura: antivirus + tope de tamaño (blueprint «upload → antivirus»).
    # Siempre detecta la firma estándar EICAR (sin infra). Si hay un daemon ClamAV
    # configurado (host/puerto o socket) y la librería `clamd`, también lo usa.
    antivirus_enabled: bool = True
    clamav_host: str = ""           # ej. 127.0.0.1 — si vacío y hay socket, usa unix
    clamav_port: int = 3310
    clamav_socket: str = ""         # ej. /var/run/clamav/clamd.ctl (unix socket)
    max_upload_mb: int = 25         # tope de tamaño por archivo subido (0 = sin tope)

    # Fine-tuning ligero (LoRA) — Fase 5 del blueprint. El andamiaje (datasets,
    # anonimización, versionado, evals) es independiente de la GPU. El entrenamiento
    # se despacha a un trainer externo (servidor con GPU, App de NaN o webhook n8n);
    # si no hay backend, el job queda 'simulado' (modo laboratorio).
    finetune_enabled: bool = False
    finetune_trainer_url: str = ""          # endpoint que ejecuta el entrenamiento LoRA
    finetune_trainer_key: str = ""          # header de auth opcional para el trainer
    finetune_default_base_model: str = "llama3.1"
    # Hiperparámetros LoRA por defecto (mapeados a las env vars de train-lora.sh:
    # ITERS/BATCH/LR/NUM_LAYERS). Sobreescribibles por el wrapper del trainer.
    finetune_iters: int = 600
    finetune_batch: int = 4
    finetune_learning_rate: str = "1e-5"
    finetune_num_layers: int = 16

    # Provider resilience: fallback order tried when a route's adapter fails.
    fallback_order: str = "vpc,open,local"

    # Token efficiency (cost control). Before sending large context to an external
    # premium model, condense it with the cheap/open route so premium pays for a
    # small input. `max_tokens_per_request` caps total tokens per call (0 = no cap).
    condense_enabled: bool = True
    condense_threshold_chars: int = 6000   # ~1.5k tokens; above this we condense
    max_tokens_per_request: int = 0        # 0 = sin tope; >0 aplica presupuesto

    # RAG reranking: after embedding retrieval, reorder candidates with a
    # cross-encoder reranker (NaN `/rerank`, Qwen3-Reranker) for precision.
    # Uses the open provider's base_url + api key. Disabled until enabled.
    rerank_enabled: bool = False
    rerank_model: str = "rerank"
    rerank_candidates: int = 20            # cuántos candidatos (por embeddings) se reordenan

    # When a private route (local/VPC) has NO real provider configured, allow the
    # router to climb to the best available real provider (open/premium) instead
    # of returning the offline MOCK. Opt-in: this lets cloud models handle data
    # that would otherwise stay private, so enable it only when that trade-off is
    # acceptable (e.g. while a local Ollama/VPC model is not yet connected).
    allow_cloud_fallback: bool = False

    # Public URL of the web portal — used to redirect the browser back after an
    # OAuth callback (mailbox connection). Defaults to the production domain.
    app_public_url: str = "https://plataforma.maestroai.mx"

    # Mailbox/calendar OAuth — Microsoft (Outlook/Graph) and Google (Gmail).
    # Set client id/secret + redirect uri (must match the app registration) to
    # enable "Conectar correo". Disabled until configured.
    microsoft_oauth_enabled: bool = False
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant: str = "common"   # 'common' for personal + work accounts
    microsoft_redirect_uri: str = ""   # e.g. https://<api>/oauth/microsoft/callback
    # Read (summary, OneDrive/Excel, SharePoint) + write (action toolkit: send
    # mail, create events, Teams, append a Excel).
    microsoft_scopes: str = (
        "offline_access User.Read Mail.Read Mail.Send "
        "Calendars.ReadWrite ChannelMessage.Send "
        "Files.ReadWrite.All Sites.Read.All"
    )

    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""      # e.g. https://<api>/oauth/google/callback
    # Read (summary + Drive context) + write (action toolkit: send mail, create
    # events, append to Sheets).
    google_scopes: str = (
        "openid email "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/calendar.events "
        "https://www.googleapis.com/auth/drive.readonly "
        "https://www.googleapis.com/auth/spreadsheets"
    )

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
