"""n8n self-hosted workflow integration (blueprint §4/§9), multi-tenant.

Hybrid resolution: a tenant with its own n8n config (base URL + encrypted token)
uses it; otherwise the global n8n (env) is used; otherwise the run is simulated.
The governed pipeline (classification, PII, RAG, router, encryption, audit) stays
inside the API — n8n only receives a minimal, parameterized payload.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..models import Tenant
from ..security.crypto import decrypt


@dataclass
class N8nConfig:
    enabled: bool
    base_url: str = ""
    api_key: str = ""
    auth_header: str = "X-N8N-API-KEY"
    source: str = "off"       # "tenant" | "global" (managed) | "off"
    path_prefix: str = ""     # managed n8n isolates tenants via path prefix


@dataclass
class WorkflowRun:
    triggered: bool
    status: str          # "completed" | "failed" | "simulated"
    source: str = "off"  # which n8n was used
    detail: str = ""
    response: dict | None = None


def resolve_n8n(tenant: Tenant) -> N8nConfig:
    """Pick the tenant's own n8n if configured (BYO), else the managed one, else off.

    Managed (global) n8n is the zero-config default: tenants share one instance
    but are isolated by a per-tenant webhook path prefix.
    """
    if tenant.n8n_webhook_base_url:
        return N8nConfig(
            enabled=True,
            base_url=tenant.n8n_webhook_base_url,
            api_key=decrypt(tenant.n8n_api_key_enc, tenant.id) if tenant.n8n_api_key_enc else "",
            auth_header=tenant.n8n_auth_header or settings.n8n_auth_header,
            source="tenant",
            # Si MaestroAI aprovisionó los workflows en su propio n8n, viven bajo el
            # path con prefijo del tenant ({tenant_id}/{workflow}); si el tenant
            # trajo sus propios flujos con paths simples, no lleva prefijo.
            path_prefix=tenant.id if tenant.n8n_provisioned else "",
        )
    if settings.n8n_enabled and settings.n8n_webhook_base_url:
        return N8nConfig(
            enabled=True,
            base_url=settings.n8n_webhook_base_url,
            api_key=settings.n8n_api_key,
            auth_header=settings.n8n_auth_header,
            source="global",
            path_prefix=tenant.id,  # managed: isolate tenants by path
        )
    return N8nConfig(enabled=False, source="off")


def trigger_workflow(cfg: N8nConfig, workflow_id: str, payload: dict, webhook_path: str | None = None) -> WorkflowRun:
    """Fire the resolved n8n webhook, or simulate when disabled."""
    if not cfg.enabled:
        return WorkflowRun(triggered=False, status="simulated", source="off",
                           detail="n8n no configurado; ejecución simulada")

    import httpx

    path = webhook_path or (f"{cfg.path_prefix}/{workflow_id}" if cfg.path_prefix else workflow_id)
    url = f"{cfg.base_url.rstrip('/')}/{path}"
    headers = {cfg.auth_header: cfg.api_key} if cfg.api_key else {}
    try:  # pragma: no cover - network path
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text[:500]}
        return WorkflowRun(triggered=True, status="completed", source=cfg.source,
                           detail=f"n8n {resp.status_code}", response=body)
    except Exception as exc:  # pragma: no cover - network path
        return WorkflowRun(triggered=True, status="failed", source=cfg.source, detail=f"n8n error: {exc}")
