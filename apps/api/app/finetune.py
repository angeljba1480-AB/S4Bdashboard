"""Fine-tuning ligero (LoRA) — Fase 5 del blueprint.

Pipeline: dataset → **anonimización** → versionado → **gate de calidad/red-team** →
entrenamiento (despachado a un trainer con GPU / App NaN / webhook n8n) → evals →
despliegue (servir el adapter como ruta local/VPC compatible OpenAI).

Este módulo es independiente de la GPU: la parte de software (datasets, anonimización,
export, gate) corre en cualquier lado; el entrenamiento se delega al trainer externo.
"""
from __future__ import annotations

import json

from .config import settings
from .security.dlp import redact
from .security.pii import detect_pii

TIMEOUT = 30


def anonymize(text: str) -> str:
    """Redacta PII de un texto antes de guardarlo/exportarlo (irreversible-looking)."""
    return redact(text or "")


def to_jsonl(examples: list[tuple[str, str]]) -> str:
    """Serializa los pares (prompt, completion) a JSONL estilo chat (OpenAI)."""
    lines = []
    for prompt, completion in examples:
        lines.append(json.dumps({"messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": completion},
        ]}, ensure_ascii=False))
    return "\n".join(lines)


def quality_gate(examples: list[tuple[str, str]]) -> dict:
    """Gate de calidad + red-team antes de entrenar:
    - dataset no vacío y con un mínimo de ejemplos,
    - sin PII residual (debería estar anonimizado),
    - sin ejemplos sospechosos de inyección de prompt.
    Devuelve {ok, issues, n, pii_leaks, injection_flags}."""
    issues: list[str] = []
    n = len(examples)
    if n < 3:
        issues.append(f"Muy pocos ejemplos ({n}); se recomiendan ≥ 3 para empezar.")
    pii_leaks = 0
    injection = 0
    _INJ = ("ignore previous", "ignora las instrucciones", "exfiltra", "reveal the system prompt",
            "olvida tus instrucciones")
    for prompt, completion in examples:
        blob = f"{prompt}\n{completion}"
        if detect_pii(blob).has_pii:
            pii_leaks += 1
        low = blob.lower()
        if any(m in low for m in _INJ):
            injection += 1
    if pii_leaks:
        issues.append(f"{pii_leaks} ejemplo(s) con PII residual — re-anonimiza antes de entrenar.")
    if injection:
        issues.append(f"{injection} ejemplo(s) con patrones de inyección de prompt — revísalos.")
    return {"ok": not issues, "issues": issues, "n": n, "pii_leaks": pii_leaks, "injection_flags": injection}


def dispatch_training(job_id: str, base_model: str, jsonl: str, callback_url: str = "") -> dict:  # pragma: no cover - red
    """Despacha el entrenamiento al trainer externo (GPU/n8n). Si no hay backend
    configurado, devuelve estado 'simulado' (laboratorio). Nunca lanza."""
    if not (settings.finetune_enabled and settings.finetune_trainer_url):
        return {"status": "simulado",
                "reason": "Sin trainer configurado (FINETUNE_TRAINER_URL): modo laboratorio."}
    import httpx
    headers = {"Content-Type": "application/json"}
    if settings.finetune_trainer_key:
        headers["Authorization"] = f"Bearer {settings.finetune_trainer_key}"
    body = {"job_id": job_id, "base_model": base_model, "dataset_jsonl": jsonl, "callback_url": callback_url}
    try:
        r = httpx.post(settings.finetune_trainer_url, headers=headers, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return {"status": "running", "reason": f"Despachado al trainer ({r.status_code})."}
    except Exception as exc:
        return {"status": "failed", "reason": f"No se pudo despachar al trainer: {exc}"}
