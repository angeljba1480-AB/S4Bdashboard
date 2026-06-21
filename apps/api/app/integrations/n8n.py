"""n8n self-hosted workflow integration (blueprint §4: Workflows = n8n).

Triggers an n8n workflow by POSTing to its webhook. Each platform workflow id
maps to an n8n webhook at ``{N8N_WEBHOOK_BASE_URL}/{webhook_path}`` (default
webhook_path = the workflow id). Optional header auth via N8N_API_KEY.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings


@dataclass
class WorkflowRun:
    triggered: bool
    status: str          # "completed" | "failed" | "simulated"
    detail: str = ""
    response: dict | None = None


def is_enabled() -> bool:
    return bool(settings.n8n_enabled and settings.n8n_webhook_base_url)


def trigger_workflow(workflow_id: str, payload: dict, webhook_path: str | None = None) -> WorkflowRun:
    """Fire an n8n webhook. Falls back to a clear failure detail on error."""
    if not is_enabled():
        return WorkflowRun(triggered=False, status="simulated",
                           detail="n8n no habilitado; ejecución simulada")

    import httpx

    path = webhook_path or workflow_id
    url = f"{settings.n8n_webhook_base_url.rstrip('/')}/{path}"
    headers = {settings.n8n_auth_header: settings.n8n_api_key} if settings.n8n_api_key else {}
    try:  # pragma: no cover - network path
        resp = httpx.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text[:500]}
        return WorkflowRun(triggered=True, status="completed",
                           detail=f"n8n {resp.status_code}", response=body)
    except Exception as exc:  # pragma: no cover - network path
        return WorkflowRun(triggered=True, status="failed", detail=f"n8n error: {exc}")
