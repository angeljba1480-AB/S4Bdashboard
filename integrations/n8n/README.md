# Integración n8n — Trainer LoRA (laboratorio MLX)

Conecta MaestroAI con tu laboratorio local (`ai-local-lab-mac`) para entrenar
adapters LoRA con MLX y servirlos en Ollama, disparado desde un job de
fine-tuning de la plataforma.

## Archivos
- **`lora-trainer.workflow.json`** — workflow de n8n listo para importar
  (Webhook `POST /webhook/lora-train` → empaqueta el payload → ejecuta el wrapper →
  responde). Impórtalo en n8n: *Workflows → Import from File*.
- **`lora-train-wrapper.sh`** — puente que corre en tu Mac: recibe el payload por
  stdin, escribe `train.jsonl`/`valid.jsonl`, mapea hiperparámetros a las env vars de
  `train-lora.sh`/`fuse-lora.sh`, entrena, fusiona, registra en Ollama y hace el
  **callback** a MaestroAI. Cópialo a `ai-local-lab-mac/scripts/` y `chmod +x`.

## Puesta en marcha
1. **Importa** `lora-trainer.workflow.json` en n8n y actívalo.
2. **Copia** `lora-train-wrapper.sh` a `~/ai-local-lab-mac/scripts/` (`chmod +x`).
   Ajusta `LAB_DIR` y `OLLAMA_BASE_URL` (tu URL de **túnel** a Ollama) si difieren.
   Requiere `jq` (`brew install jq`).
3. **Expón** n8n y Ollama por un túnel (Cloudflare/ngrok) para que el cloud los alcance.
4. En MaestroAI (Render/`.env` del backend):
   ```
   FINETUNE_ENABLED=true
   FINETUNE_TRAINER_URL=https://<tu-n8n>/webhook/lora-train
   FINETUNE_TRAINER_KEY=<token opcional>
   FINETUNE_DEFAULT_BASE_MODEL=llama3.2:3b
   ```
5. Lanza un **job** desde *Fine-tuning* → el wrapper entrena y, al terminar, el job
   queda `completed` con la URL de Ollama servida y el nombre del modelo.

> El payload, el mapeo de variables y el formato del callback están documentados en
> [`docs/FINETUNING-SETUP.md`](../../docs/FINETUNING-SETUP.md). Los datasets y pesos
> **no se suben a Git** (viven solo en tu laboratorio).
