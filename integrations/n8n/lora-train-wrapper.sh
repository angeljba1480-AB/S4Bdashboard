#!/bin/bash
#
# lora-train-wrapper.sh
# Puente entre MaestroAI (job de fine-tuning) y el laboratorio MLX local.
# Lo dispara el workflow de n8n (integrations/n8n/lora-trainer.workflow.json):
# recibe el payload JSON por stdin, escribe train/valid.jsonl, mapea los
# hiperparámetros a las env vars de train-lora.sh / fuse-lora.sh, entrena, fusiona
# y registra el modelo en Ollama, y al final hace el callback a MaestroAI.
#
# Coloca este archivo en ai-local-lab-mac/scripts/ y dale permisos: chmod +x.
#
set -euo pipefail

LAB_DIR="${LAB_DIR:-$HOME/ai-local-lab-mac}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434/v1}"   # usa tu URL de túnel
cd "$LAB_DIR"

# Activa el entorno MLX si existe.
[ -f "$HOME/.venvs/mlx/bin/activate" ] && source "$HOME/.venvs/mlx/bin/activate"

PAYLOAD="$(cat)"   # el JSON llega por stdin (n8n: base64 --decode | bash wrapper)

JOB=$(jq -r '.job_id'        <<<"$PAYLOAD")
CB=$(jq  -r '.callback_url'  <<<"$PAYLOAD")
export MODEL=$(jq -r '.mlx_model'    <<<"$PAYLOAD")
export OLLAMA_NAME=$(jq -r '.ollama_name' <<<"$PAYLOAD")
export DATA="datasets/$JOB"
export ADAPTER="adapters/$JOB"
export FUSED_DIR="fused_model/$JOB"
export ITERS=$(jq      -r '.hyperparams.iters'         <<<"$PAYLOAD")
export BATCH=$(jq      -r '.hyperparams.batch'         <<<"$PAYLOAD")
export LR=$(jq         -r '.hyperparams.learning_rate' <<<"$PAYLOAD")
export NUM_LAYERS=$(jq -r '.hyperparams.num_layers'    <<<"$PAYLOAD")

mkdir -p "$DATA"
jq -r '.train_jsonl' <<<"$PAYLOAD" > "$DATA/train.jsonl"
jq -r '.valid_jsonl' <<<"$PAYLOAD" > "$DATA/valid.jsonl"
# MLX-LM exige valid.jsonl no vacío: si vino vacío, reutiliza el set de train.
[ -s "$DATA/valid.jsonl" ] || cp "$DATA/train.jsonl" "$DATA/valid.jsonl"

callback() {  # $1=status  $2=reason
  curl -fsS -X POST "$CB" -H 'Content-Type: application/json' -d "$(jq -n \
    --arg s "$1" --arg base "$OLLAMA_BASE_URL" --arg m "$OLLAMA_NAME" \
    --arg job "$JOB" --arg reason "${2:-}" \
    '{status:$s, adapter_uri:("file://adapters/"+$job),
      serve_base_url:$base, metrics:{served_model:$m, reason:$reason}}')" || true
}
trap 'callback failed "error en el entrenamiento"' ERR

echo "=== MaestroAI LoRA job $JOB → $OLLAMA_NAME ($MODEL) ==="
./scripts/train-lora.sh        # entrena el adapter LoRA (MLX)
./scripts/fuse-lora.sh         # fusiona → GGUF → ollama create $OLLAMA_NAME

callback completed "ok"
echo "Listo. Modelo servido en Ollama como '$OLLAMA_NAME'. Callback enviado a MaestroAI."
