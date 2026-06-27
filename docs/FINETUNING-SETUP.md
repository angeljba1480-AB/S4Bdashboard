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

## Laboratorio en tu computadora (GPU + Ollama + n8n)
Tienes lo necesario: **GPU**, **Ollama** y **n8n self-hosted**.

### Variables (Render o `.env` del backend)
```
FINETUNE_ENABLED      = true
FINETUNE_TRAINER_URL  = https://<tu-n8n>/webhook/lora-train   # o tu servicio de training
FINETUNE_TRAINER_KEY  = <token opcional>
FINETUNE_DEFAULT_BASE_MODEL = llama3.1
```

### El trainer (un workflow n8n o un script en la GPU)
Recibe `{job_id, base_model, dataset_jsonl, callback_url}` y:
1. Guarda el JSONL y lanza el entrenamiento **LoRA/PEFT** (p. ej. `transformers` +
   `peft` + `bitsandbytes`) sobre el base (un modelo HF equivalente al de Ollama).
2. Exporta el adapter (o un modelo fusionado) a un **Modelfile de Ollama** o a un
   servidor **vLLM**.
3. Llama de vuelta a `callback_url` (`/finetune/jobs/{id}/callback`) con el resultado.

> Ejemplo de Modelfile de Ollama para servir el resultado:
> ```
> FROM llama3.1
> ADAPTER ./adapters/<job_id>
> ```
> `ollama create maestro-tono -f Modelfile` → exponer Ollama (`/v1`) y conectarlo como
> ruta **local**.

## Privacidad
- Los datasets se **anonimizan** antes de salir; el gate bloquea PII residual e inyección.
- El entrenamiento corre en **tu** GPU; el dato sensible **no sale** a la nube.
- Todo queda **auditado** (eventos `finetune`).

## Endpoints
`POST /finetune/datasets` · `/datasets/{id}/examples` · `/datasets/{id}/from-memory` ·
`GET /datasets/{id}/export` (JSONL) · `POST /datasets/{id}/check` · `POST /finetune/jobs` ·
`GET /finetune/jobs` · `POST /finetune/jobs/{id}/callback`. Solo **ADMIN/DEVOPS**.

_MaestroAI · Guía de fine-tuning (LoRA)._
