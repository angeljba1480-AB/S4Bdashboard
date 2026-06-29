# Proveedor NaN Builders — contexto de integración

> Referencia del proveedor **abierto** de MaestroAI (ruta `open`). NaN Builders
> ofrece una API **compatible con OpenAI**. Última actualización: 2026-06-27.

- **Base URL**: `https://api.nan.builders/v1`
- **Auth**: header `Authorization: Bearer <api-key>` (key personal e intransferible).
- **Enterprise (Helmcode)**: misma API en `https://api.helmcode.com/v1` (resto idéntico).
- En MaestroAI se configura en *Admin → Modelos externos → Abierto* (Base URL +
  modelo + API key, cifrada) y se verifica con **Probar conexión**.

## Endpoints disponibles (API)
| Endpoint | Método | Uso |
|---|---|---|
| `/v1/models` | GET | Listar modelos de tu key |
| `/v1/chat/completions` | POST | Chat (streaming, tools, vision, reasoning, structured outputs) |
| `/v1/completions` | POST | Text completion (legacy) |
| `/v1/embeddings` | POST | Embeddings vectoriales (4096 dim) |
| `/v1/rerank` (`/v2/rerank`) | POST | Reranking semántico para RAG |
| `/v1/audio/speech` | POST | Text-to-speech (TTS) |
| `/v1/audio/transcriptions` | POST | Speech-to-text (STT) |
| `/v1/responses` | POST | Responses estilo OpenAI |
| `/v1/images/generations` | POST | **Text-to-image** (flux-2-klein) |
| `/v1/images/edits` | POST | **Image-to-image** (flux-2-klein, hasta 4 refs) |

> ✅ **Generación de imágenes disponible** (`flux-2-klein`, modelo de difusión FLUX).
> text→image (`/v1/images/generations`) e image→image (`/v1/images/edits`),
> compatibles con la Images API de OpenAI. **Requiere membresía tier _inference_**
> (las keys *community* reciben `403 tier_restricted`). Tamaños múltiplos de 16 entre
> 256–1536 px; **1–4** imágenes por request (`n`); salida `url` (R2, ~60 min) o
> `b64_json`; extensiones `seed` y `guidance` (vía `extra_body`). Cuota: **100
> requests/mes/miembro** + 1 req/s (burst 3), independiente de la cuota de chat.
> MaestroAI ya lo usa en *Generar imágenes* (`settings.image_model = flux-2-klein`).

> ⛔ **No hay endpoint de fine-tuning / LoRA / entrenamiento** en la API de NaN
> (verificado contra el reference completo: solo chat, completions, embeddings,
> rerank, audio, responses, images). El fine-tuning de MaestroAI se entrena en infra
> propia del cliente (lab MLX / GPU externa) y se sirve como ruta local/VPC. Cualquier
> afirmación de "LoRA en la GPU de NaN" (p. ej. de buscadores con IA) **no está
> respaldada por su API documentada**.

## Modelos publicados
| Modelo | Tipo | Contexto | Capacidades |
|---|---|---|---|
| `deepseek-v4-flash` | MoE 284B/21B (FP8) | 1M | chat, streaming, tools, reasoning (`reasoning_effort`) |
| `mimo-v2.5` | MoE 310B/15B (FP8) | 1M | chat, tools, reasoning, **visión + audio input** (omnimodal) |
| `qwen3.6` | MoE 35B/3B (FP8) | 256K | chat, streaming, tools, visión, reasoning (default ON) — **modelo principal** |
| `gemma4` | MoE 26B/4B (FP8) | 256K | chat, streaming, visión, reasoning (opt-in) |
| `qwen3-embedding` | 8B | — | embeddings (4096 dim, 100+ idiomas, ES↔EN 0.915) |
| `rerank` | Qwen3-Reranker-8B | — | reranking RAG (`/v1/rerank`), 100+ idiomas, código |
| `kokoro` | TTS 82M | — | text-to-speech, voces ES `ef_dora`/`em_alex`, <1s latencia |
| `whisper` | large-v3 | — | speech-to-text, 99+ idiomas, WER ES ~3.2% |
| `flux-2-klein` | Diffusion (FLUX) | — | **text→image / image→image** (`/v1/images/*`), tier *inference* |

### Reasoning (control por modelo)
- `qwen3.6` / `gemma4`: `extra_body={"chat_template_kwargs": {"enable_thinking": bool}}`
  (qwen ON por defecto, gemma OFF). Devuelve `reasoning_content`.
- `deepseek-v4-flash`: `reasoning_effort` = `low|medium|high` (top-level, default `medium`).
- `mimo-v2.5`: siempre activo, no configurable hoy.

### Structured outputs
`response_format` estándar OpenAI (`json_object` y `json_schema` con `strict`) en
`qwen3.6` y `gemma4`.

## Rate limits (por API key)
- **60 rpm**, **3** peticiones en paralelo.
- **1.5M tpm** por modelo de chat (`deepseek-v4-flash`, `mimo-v2.5`, `qwen3.6`, `gemma4`).
- `rerank`: 1000 rpm.
- Cuota mensual: **500M tokens/miembro** en `deepseek-v4-flash` y `mimo-v2.5`.

## Errores
Formato OpenAI (`{"error": {message, type, param, code}}`). Códigos: `401` auth,
`404` modelo inexistente, `429` rate limit, `500` interno/upstream, `524` timeout
(típico en audios largos > 2 min en STT).

## Otros productos NaN Cloud (no son la API de inferencia)
- **Agents** (Hermes): agente conversacional en **microVM** (QEMU+KVM, kernel propio,
  disco **ext4 20 GiB persistente** en block-mode, **root** completo, aislado del host)
  conectado a **Telegram**. Setup: bot con @BotFather → `cloud.nan.builders/agents/new`
  (nombre, tipo Hermes, token, modelo, *soul*/system prompt) → ~30 s a *Running*.
  Panel: **Console** (terminal web bash sobre WebSocket; 1 sesión, idle 10 min, máx
  30 min), **Files** (subida drag-and-drop a `/persist/uploads/`, ≤ 200 MiB/fichero),
  **Observability** (Logs/Events/Metrics), **Web** (exponer HTTP en `*.apps.nan.builders`
  + Hermes UI con password), **Env** (vars; `OPENAI_API_KEY` y `TELEGRAM_BOT_TOKEN`
  protegidas). **Recursos: 200m–1 vCPU, 512 Mi–2 GiB RAM, 20 GiB disco. SIN GPU.**
  1 agente por miembro.
  > ⚠️ Implicación para MaestroAI: las microVM son **CPU-only** (sin GPU) → **no sirven
  > para entrenar LoRA**. Confirma que el entrenamiento debe correr en infra propia del
  > cliente (lab MLX / GPU externa), no en NaN.
- **Apps**: despliega tus propias apps desde **GitHub** (requiere **Dockerfile** en la raíz)
  dentro de un **Space** (entorno aislado tuyo con cuota agregada de CPU/RAM/disco). Build de
  la imagen → entorno aislado → **dominio público HTTPS** (`*.apps.nan.builders`), en un clic.
  **Auto-deploy** en cada `git push` a la rama. Expone HTTP (indicas el puerto) o corre como
  *worker* (sin URL). Por app por defecto 500m CPU / 500 MiB RAM (ajustable en *Advanced*);
  disco persistente vía PVC solo si la marcas *persistent*. Env vars de runtime y build.
  - **Tiers** (cuota agregada del Space): **Basic** 2 vCPU / 4 GiB / 20 GiB / 5 pods —
    *gratis con la suscripción de inferencia*, o $6/mes; **Medium** 4 vCPU / 8 GiB / 40 GiB /
    10 pods — $12/mes; **Large** 4 vCPU / 16 GiB / 80 GiB / 20 pods — $24/mes. Sub/baja de tier
    en caliente. (Apps y Spaces en **Beta**.)
  > 💡 Implicación para MaestroAI: un **Space de NaN** es hosting **aislado dentro del mismo
  > proveedor que ya usamos**. Sirve como alternativa a Render/Vercel para componentes propios
  > y, para privacidad, para hospedar un **embebedor/servicio on-prem-equivalente** sin túnel a
  > una Mac (CPU-only: bien para embeddings/API, **no para entrenar LoRA con GPU**).

---

## Qué usa MaestroAI de NaN hoy
- ✅ **Chat / generación** (ruta `open`) → `qwen3.6` por defecto (compatible OpenAI).
  Es el modelo barato de la **cascada** y de la **condensación** de contexto.
- ✅ **rerank** (Qwen3-Reranker vía `/rerank`) → reordena el RAG para más precisión
  (embedding → rerank → LLM). Toggle en *Admin → Eficiencia de tokens*.
- ✅ **Imágenes (flux-2-klein)** → *Generar imágenes* usa `/v1/images/generations`
  (ruta OpenAI estándar) con `settings.image_model = flux-2-klein`. Requiere tier
  *inference* en la key. (image→image vía `/v1/images/edits` queda como siguiente paso.)
- 🔜 **Candidatos de alto valor** (endpoints reales de NaN, aún sin cablear):
  - **TTS (kokoro)** → narrar salidas en español; **STT (whisper)** → transcribir audio.
  - **embeddings (qwen3-embedding)** → fuente de embeddings del RAG.
