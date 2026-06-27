# Integración on-prem — conectar modelos y servicios locales del cliente

> **Feature**: cuando el cliente tiene infraestructura local (modelos, RAG, workflows),
> MaestroAI se integra con ella en vez de obligar a usar la nube. Lo confidencial se
> procesa **on-prem** y nunca sale. Referencia de laboratorio: `ai-local-lab-mac`
> (Docker + Ollama + Qdrant + AnythingLLM + n8n + LoRA con MLX).

## Idea
MaestroAI es el **gateway gobernado**; los **modelos/servicios viven donde el cliente
quiera**: en su propia máquina/servidor (on-prem) o en la nube. El **router de privacidad**
manda lo sensible a las rutas privadas (**local/VPC**) y solo lo no sensible a externas.

## Requisito de red (importante)
MaestroAI (nube/Render) no alcanza `localhost` del cliente. Dos opciones:
1. **Túnel** (Cloudflare Tunnel / ngrok) que expone el servicio local con una URL pública
   HTTPS — pones esa URL en MaestroAI. *(Para laboratorio/PoC.)*
2. **MaestroAI on-prem** (mismo Docker/VPC del cliente) — alcanza los servicios por red
   interna. *(Para producción regulada.)*

## Conectar tu laboratorio (mapa lab → MaestroAI)
| Servicio del lab | URL local | En MaestroAI |
|---|---|---|
| **Ollama** (modelos) | `http://localhost:11434` | *Admin → Modelos y conectores → Local (Ollama)*: Base URL `https://<túnel>/v1`, modelo `llama3.2:3b` o `deepseek-r1:8b` → **Probar conexión** |
| **vLLM/TGI** (si aplica) | — | ruta **VPC privada** (mismo flujo) |
| **Qdrant** (vector) | `http://localhost:6333` | `VECTOR_STORE=qdrant`, `QDRANT_URL=https://<túnel>` |
| **Embeddings** (`nomic-embed-text`) | Ollama | `EMBEDDINGS_PROVIDER=local` + base de Ollama |
| **n8n** (workflows) | `http://localhost:5678` | *Admin → n8n* (Webhook Base URL + API key) |
| **Trainer LoRA (MLX)** | `./scripts/train-lora.sh` | `FINETUNE_TRAINER_URL=https://<túnel>/webhook/lora-train` (ver `FINETUNING-SETUP.md`) |

### Pasos (Ollama como ruta local)
1. En tu Mac: `ollama serve` y `ollama pull llama3.2:3b` (o `deepseek-r1:8b`).
2. Expón Ollama: `cloudflared tunnel --url http://localhost:11434` → copia la URL `https://…`.
3. En MaestroAI: *Admin → Modelos y conectores → Local (Ollama)* → Base URL `https://…/v1`,
   modelo `llama3.2:3b`, **Activo**, Guardar → **Probar conexión** (latencia + muestra).
4. Listo: los datos **confidenciales/restringidos** ahora se procesan con tu modelo local.

## Privacidad
- El router decide la ruta por sensibilidad; lo **restringido** va a **local** y no sale.
- PII redactada/minimizada antes de cualquier salida; todo **auditado**.
- Las credenciales/URLs se guardan **cifradas**.

## Fine-tuning local (LoRA con MLX)
Tu lab entrena con **MLX-LM** y convierte a **GGUF** para servir en Ollama
(`train-lora.sh` → `fuse-lora.sh`). MaestroAI lo orquesta vía `/finetune` + el webhook del
trainer y luego sirve el adapter como **ruta local**. Detalle en `FINETUNING-SETUP.md`.

_MaestroAI · Integración on-prem (modelos y servicios locales)._
