"""Managed n8n auto-provisioning.

Non-technical tenants configure nothing: the platform creates and activates
their workflows in the managed n8n via its REST API, with tenant-isolated
webhook paths (``{tenant_id}/{workflow_id}``). Idempotent and best-effort — a
no-op when the REST API isn't configured.
"""
from __future__ import annotations

import uuid

from ..config import settings
from ..models import Tenant


def is_available() -> bool:
    return bool(settings.n8n_enabled and settings.n8n_api_base_url and settings.n8n_api_key)


def _webhook_workflow(tenant_id: str, workflow_id: str, name: str) -> dict:
    """Minimal, version-stable n8n workflow: Webhook -> NoOp (echoes input)."""
    return {
        "name": name,
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": f"{tenant_id}/{workflow_id}",
                    "responseMode": "lastNode",
                    "options": {},
                },
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [260, 300],
                "webhookId": uuid.uuid4().hex,
            },
            {
                "parameters": {},
                "name": "NoOp",
                "type": "n8n-nodes-base.noOp",
                "typeVersion": 1,
                "position": [520, 300],
            },
        ],
        "connections": {"Webhook": {"main": [[{"node": "NoOp", "type": "main", "index": 0}]]}},
        "settings": {},
    }


def ensure_tenant_workflows(tenant: Tenant, workflow_ids: list[str]) -> dict:
    """Create + activate any missing managed workflows for the tenant."""
    if not is_available():
        return {"provisioned": False, "reason": "REST API de n8n no configurada (N8N_API_BASE_URL)"}

    import httpx

    base = settings.n8n_api_base_url.rstrip("/")
    headers = {settings.n8n_auth_header: settings.n8n_api_key, "Accept": "application/json"}
    created: list[str] = []
    try:  # pragma: no cover - network path
        listing = httpx.get(f"{base}/workflows", headers=headers, timeout=20).json()
        rows = listing.get("data", listing) if isinstance(listing, dict) else listing
        existing = {w.get("name") for w in (rows or [])}

        for wid in workflow_ids:
            name = f"[PAI:{tenant.id}] {wid}"
            if name in existing:
                continue
            resp = httpx.post(f"{base}/workflows", headers=headers,
                              json=_webhook_workflow(tenant.id, wid, name), timeout=20)
            resp.raise_for_status()
            data = resp.json()
            new_id = data.get("id") or (data.get("data") or {}).get("id")
            if new_id:
                httpx.post(f"{base}/workflows/{new_id}/activate", headers=headers, timeout=20)
            created.append(wid)
        return {"provisioned": True, "created": created, "total": len(workflow_ids)}
    except Exception as exc:  # pragma: no cover - network path
        return {"provisioned": False, "reason": f"n8n REST error: {exc}"}
