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
    """Serializa los pares (prompt, completion) a JSONL estilo chat (compatible con
    OpenAI y con MLX-LM, que aceptan líneas {"messages": [...]})."""
    lines = []
    for prompt, completion in examples:
        lines.append(json.dumps({"messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": completion},
        ]}, ensure_ascii=False))
    return "\n".join(lines)


def split_jsonl(examples: list[tuple[str, str]], valid_ratio: float = 0.1) -> tuple[str, str]:
    """Divide en train/valid (MLX-LM requiere train.jsonl Y valid.jsonl). Garantiza
    al menos 1 ejemplo de validación cuando hay ≥ 2."""
    n = len(examples)
    n_valid = max(1, int(n * valid_ratio)) if n >= 2 else 0
    valid = examples[n - n_valid:] if n_valid else []
    train = examples[: n - n_valid] if n_valid else examples
    return to_jsonl(train), to_jsonl(valid)


# Catálogo de modelos open source de la industria → id MLX (mlx-community, base para
# el fine-tuning LoRA en Apple Silicon). Las claves son los nombres estilo Ollama; los
# valores, los repos 4-bit listos para MLX. Si un modelo no está, se usa el base_model
# tal cual (el cliente puede pasar cualquier repo mlx-community). Ampliable.
MLX_MODEL_MAP = {
    # --- Meta Llama ---
    "llama3.2:1b": "mlx-community/Llama-3.2-1B-Instruct-4bit",
    "llama3.2:3b": "mlx-community/Llama-3.2-3B-Instruct-4bit",
    "llama3:8b": "mlx-community/Meta-Llama-3-8B-Instruct-4bit",
    "llama3.1": "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
    "llama3.1:8b": "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
    "llama3.1:70b": "mlx-community/Meta-Llama-3.1-70B-Instruct-4bit",
    "llama3.3:70b": "mlx-community/Llama-3.3-70B-Instruct-4bit",
    # --- Mistral AI ---
    "mistral:7b": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
    "mistral-nemo:12b": "mlx-community/Mistral-Nemo-Instruct-2407-4bit",
    "mistral-small": "mlx-community/Mistral-Small-Instruct-2409-4bit",
    "mixtral:8x7b": "mlx-community/Mixtral-8x7B-Instruct-v0.1-4bit",
    # --- Alibaba Qwen ---
    "qwen2.5:3b": "mlx-community/Qwen2.5-3B-Instruct-4bit",
    "qwen2.5:7b": "mlx-community/Qwen2.5-7B-Instruct-4bit",
    "qwen2.5:14b": "mlx-community/Qwen2.5-14B-Instruct-4bit",
    "qwen2.5:32b": "mlx-community/Qwen2.5-32B-Instruct-4bit",
    "qwen2.5:72b": "mlx-community/Qwen2.5-72B-Instruct-4bit",
    "qwen2.5-coder:7b": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
    "qwen2.5-coder:14b": "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit",
    "qwen3:8b": "mlx-community/Qwen3-8B-4bit",
    "qwen3:14b": "mlx-community/Qwen3-14B-4bit",
    "qwen3:32b": "mlx-community/Qwen3-32B-4bit",
    # --- Google Gemma ---
    "gemma2:2b": "mlx-community/gemma-2-2b-it-4bit",
    "gemma2:9b": "mlx-community/gemma-2-9b-it-4bit",
    "gemma2:27b": "mlx-community/gemma-2-27b-it-4bit",
    "gemma3:4b": "mlx-community/gemma-3-4b-it-4bit",
    "gemma3:12b": "mlx-community/gemma-3-12b-it-4bit",
    "gemma3:27b": "mlx-community/gemma-3-27b-it-4bit",
    # --- Microsoft Phi ---
    "phi3:mini": "mlx-community/Phi-3-mini-4k-instruct-4bit",
    "phi3.5": "mlx-community/Phi-3.5-mini-instruct-4bit",
    "phi4": "mlx-community/phi-4-4bit",
    # --- DeepSeek (R1 distill) ---
    "deepseek-r1:1.5b": "mlx-community/DeepSeek-R1-Distill-Qwen-1.5B-4bit",
    "deepseek-r1:7b": "mlx-community/DeepSeek-R1-Distill-Qwen-7B-4bit",
    "deepseek-r1:8b": "mlx-community/deepseek-r1-distill-llama-8b-4bit",
    "deepseek-r1:14b": "mlx-community/DeepSeek-R1-Distill-Qwen-14B-4bit",
    "deepseek-r1:32b": "mlx-community/DeepSeek-R1-Distill-Qwen-32B-4bit",
    "deepseek-coder-v2:16b": "mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit",
    # --- Otros frecuentes ---
    "smollm2:1.7b": "mlx-community/SmolLM2-1.7B-Instruct-4bit",
    "yi:6b": "mlx-community/Yi-1.5-6B-Chat-4bit",
    "yi:9b": "mlx-community/Yi-1.5-9B-Chat-4bit",
}


def mlx_model_for(base_model: str) -> str:
    return MLX_MODEL_MAP.get(base_model, base_model)


def list_base_models() -> list[dict]:
    """Catálogo legible para la UI: nombre Ollama → id MLX, agrupado por familia."""
    def _family(name: str) -> str:
        for key, fam in (("llama", "Meta Llama"), ("mistral", "Mistral"), ("mixtral", "Mistral"),
                         ("qwen", "Qwen"), ("gemma", "Gemma"), ("phi", "Phi"),
                         ("deepseek", "DeepSeek"), ("smollm", "SmolLM"), ("yi", "Yi")):
            if name.startswith(key):
                return fam
        return "Otros"
    return [{"name": n, "mlx_model": m, "family": _family(n)} for n, m in MLX_MODEL_MAP.items()]


def suggest_ollama_name(dataset_name: str, version: int = 1) -> str:
    """Nombre sugerido para registrar el modelo fusionado en Ollama (OLLAMA_NAME de
    fuse-lora.sh). Slug seguro: minúsculas, guiones, sufijo de versión."""
    base = "".join(c if (c.isalnum() or c in "-_") else "-" for c in (dataset_name or "").lower())
    base = "-".join(filter(None, base.split("-"))) or "maestro"
    return f"{base}-lora-v{max(1, version)}"


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


def build_trainer_payload(job_id: str, base_model: str, examples: list[tuple[str, str]],
                          callback_url: str = "", ollama_name: str = "") -> dict:
    """Arma el payload que consume el wrapper del trainer MLX (train-lora.sh /
    fuse-lora.sh del laboratorio on-prem). El wrapper escribe `train_jsonl`/
    `valid_jsonl` a `$DATA/{train,valid}.jsonl`, usa `mlx_model` como `MODEL`,
    `ollama_name` como `OLLAMA_NAME` y mapea `hyperparams` a ITERS/BATCH/LR/
    NUM_LAYERS; al terminar hace POST a `callback_url` con el adapter y la URL de
    Ollama servida. Ver docs/FINETUNING-SETUP.md."""
    train_jsonl, valid_jsonl = split_jsonl(examples)
    return {
        "job_id": job_id,
        "base_model": base_model,                 # nombre Ollama (informativo)
        "mlx_model": mlx_model_for(base_model),    # id MLX → MODEL en train-lora.sh
        "ollama_name": ollama_name or suggest_ollama_name(base_model),
        "train_jsonl": train_jsonl,
        "valid_jsonl": valid_jsonl,
        "callback_url": callback_url,
        "hyperparams": {
            "iters": settings.finetune_iters,
            "batch": settings.finetune_batch,
            "learning_rate": settings.finetune_learning_rate,
            "num_layers": settings.finetune_num_layers,
        },
    }


def dispatch_training(job_id: str, base_model: str, examples: list[tuple[str, str]],
                      callback_url: str = "", ollama_name: str = "") -> dict:  # pragma: no cover - red
    """Despacha el entrenamiento al trainer externo (laboratorio MLX on-prem / GPU /
    webhook n8n). Si no hay backend configurado, devuelve estado 'simulado'
    (laboratorio). Nunca lanza."""
    if not (settings.finetune_enabled and settings.finetune_trainer_url):
        return {"status": "simulado",
                "reason": "Sin trainer configurado (FINETUNE_TRAINER_URL): modo laboratorio."}
    import httpx
    headers = {"Content-Type": "application/json"}
    if settings.finetune_trainer_key:
        headers["Authorization"] = f"Bearer {settings.finetune_trainer_key}"
    body = build_trainer_payload(job_id, base_model, examples, callback_url, ollama_name)
    try:
        r = httpx.post(settings.finetune_trainer_url, headers=headers, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return {"status": "running", "reason": f"Despachado al trainer MLX ({r.status_code})."}
    except Exception as exc:
        return {"status": "failed", "reason": f"No se pudo despachar al trainer: {exc}"}
