# Fine-tuning ligero (LoRA) — guía y laboratorio local

> Fase 5 del blueprint: *dataset → anonimización → versionado → entrenamiento LoRA →
> evals → red team → despliegue*. Para **comportamiento/formato/tareas repetitivas**
> (el conocimiento va por RAG, no por fine-tuning).

El **andamiaje** vive en la plataforma (datasets, anonimización, gate de calidad/
red-team, export JSONL, jobs). El **entrenamiento** se delega a un *trainer* externo
con GPU; el **adapter** resultante se sirve como ruta **local/VPC** (Ollama/vLLM).

## Flujo end-to-end
1. **Dataset** (`/finetune/datasets`): crea uno y añade ejemplos `(prompt, completion)`.
   Cada ejemplo se **anonimiza** (PII redactada) al guardarse. También puedes construirlo
   desde **Memoria** (`/datasets/{id}/from-memory`).
2. **Gate** (`/datasets/{id}/check`): valida mínimo de ejemplos, **sin PII residual** y
   **sin patrones de inyección**. Si pasa, el dataset queda `ready`.
3. **Job** (`/finetune/jobs`): exporta el dataset a JSONL (chat) y lo **despacha al
   trainer**. Sin trainer configurado, el job queda `simulado` (modo laboratorio).
4. **Trainer** (tu GPU): entrena el adapter LoRA y al terminar llama a
   `POST /finetune/jobs/{id}/callback` con `status`, `adapter_uri`, `serve_base_url` y `metrics`.
5. **Servir**: el adapter se sirve en un endpoint compatible OpenAI (Ollama/vLLM) y se
   conecta como **ruta local/VPC** en *Admin → Modelos externos* (así el router de
   privacidad lo usa para datos confidenciales sin salir a la nube).

## Laboratorio en tu computadora (Apple Silicon · MLX + Ollama + n8n)
Tu laboratorio (`ai-local-lab-mac`) entrena con **MLX-LM** (`train-lora.sh` →
`fuse-lora.sh`) y sirve en **Ollama**. MaestroAI despacha el job hacia ese trainer.

### Variables (Render o `.env` del backend)
```
FINETUNE_ENABLED      = true
FINETUNE_TRAINER_URL  = https://<tu-n8n>/webhook/lora-train   # o tu servicio de training
FINETUNE_TRAINER_KEY  = <token opcional>
FINETUNE_DEFAULT_BASE_MODEL = llama3.2:3b
# Hiperparámetros LoRA (se mapean a las env vars de train-lora.sh):
FINETUNE_ITERS=600  FINETUNE_BATCH=4  FINETUNE_LEARNING_RATE=1e-5  FINETUNE_NUM_LAYERS=16
```

### Payload que envía MaestroAI al trainer
`POST FINETUNE_TRAINER_URL` (con `Authorization: Bearer FINETUNE_TRAINER_KEY` si está):
```json
{
  "job_id": "…",
  "base_model": "llama3.2:3b",
  "mlx_model": "mlx-community/Llama-3.2-3B-Instruct-4bit",
  "ollama_name": "tono-comercial-lora-v1",
  "train_jsonl": "{\"messages\":[…]}\n…",
  "valid_jsonl": "{\"messages\":[…]}\n…",
  "callback_url": "https://<api>/finetune/jobs/<job_id>/callback",
  "hyperparams": {"iters":600,"batch":4,"learning_rate":"1e-5","num_layers":16}
}
```
> `base_model` (nombre Ollama) se traduce a `mlx_model` (id MLX, ver `MLX_MODEL_MAP`
> en `app/finetune.py`). El dataset ya viene **dividido** en `train_jsonl`/`valid_jsonl`
> porque `mlx_lm.lora` exige `train.jsonl` **y** `valid.jsonl`.

### Wrapper del trainer (script en la Mac, disparado por n8n)
> **Listos para usar:** `integrations/n8n/lora-trainer.workflow.json` (impórtalo en n8n)
> y `integrations/n8n/lora-train-wrapper.sh` (cópialo a `ai-local-lab-mac/scripts/`).
> Ver `integrations/n8n/README.md`. El snippet de abajo es la versión mínima explicada.

Mapea el payload a las env vars de `train-lora.sh`/`fuse-lora.sh` y hace el callback:
```bash
#!/bin/bash
set -euo pipefail
PAYLOAD="$(cat)"                      # el JSON llega por stdin (n8n → Execute Command)
JOB=$(jq -r .job_id      <<<"$PAYLOAD")
CB=$(jq  -r .callback_url <<<"$PAYLOAD")
export MODEL=$(jq -r .mlx_model     <<<"$PAYLOAD")
export OLLAMA_NAME=$(jq -r .ollama_name <<<"$PAYLOAD")
export DATA="datasets/$JOB"  ADAPTER="adapters/$JOB"
export ITERS=$(jq -r .hyperparams.iters       <<<"$PAYLOAD")
export BATCH=$(jq -r .hyperparams.batch       <<<"$PAYLOAD")
export LR=$(jq    -r .hyperparams.learning_rate <<<"$PAYLOAD")
export NUM_LAYERS=$(jq -r .hyperparams.num_layers <<<"$PAYLOAD")

mkdir -p "$DATA"
jq -r .train_jsonl <<<"$PAYLOAD" > "$DATA/train.jsonl"
jq -r .valid_jsonl <<<"$PAYLOAD" > "$DATA/valid.jsonl"

./scripts/train-lora.sh                                   # entrena el adapter LoRA
./scripts/fuse-lora.sh                                    # fusiona → GGUF → ollama create

# Reporta el resultado a MaestroAI (Ollama servido por túnel; ver ONPREM-LAB.md)
curl -fsS -X POST "$CB" -H 'Content-Type: application/json' -d "$(jq -n \
  --arg base "${OLLAMA_BASE_URL:-http://localhost:11434/v1}" --arg m "$OLLAMA_NAME" \
  '{status:"completed", adapter_uri:("file://adapters/"+env.JOB),
    serve_base_url:$base, metrics:{served_model:$m}}')"
```
> El `valid.jsonl` puede quedar vacío si el dataset es muy chico (< 2 ejemplos); con
> ≥ 3 (mínimo del gate) siempre hay validación. El `serve_base_url` del callback es la
> **URL de Ollama por túnel** y `metrics.served_model` es el `OLLAMA_NAME` a usar como
> `model` en la ruta local/VPC.

> El JSONL que exporta MaestroAI usa el **formato chat** (`{"messages":[…]}`), que es
> justo el que recomienda la guía del laboratorio (`docs/lora-training.md` del repo
> `ai-local-lab-mac`, sección 4). El `mlx_model` por defecto (`llama3.2:3b` →
> `mlx-community/Llama-3.2-3B-Instruct-4bit`) coincide con el default de `train-lora.sh`.

## Privacidad
- Los datasets se **anonimizan** antes de salir; el gate bloquea PII residual e inyección.
- El entrenamiento corre en **tu** GPU; el dato sensible **no sale** a la nube.
- Todo queda **auditado** (eventos `finetune`).

## Endpoints
`POST /finetune/datasets` · `/datasets/{id}/examples` · `/datasets/{id}/from-memory` ·
`GET /datasets/{id}/export` (JSONL) · `POST /datasets/{id}/check` · `POST /finetune/jobs` ·
`GET /finetune/jobs` · `POST /finetune/jobs/{id}/callback`. Solo **ADMIN/DEVOPS**.

_MaestroAI · Guía de fine-tuning (LoRA)._
