# Proveedor NaN Builders — contexto de integración

> Referencia del proveedor **abierto** de MaestroAI (ruta `open`). NaN Builders
> ofrece una API **compatible con OpenAI**. Última actualización: 2026-06-25.

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

> ⚠️ **No hay endpoint de generación de imágenes en la API.** El *Generate*
> (text-to-image, FLUX.2 [klein] 9B) de `cloud.nan.builders/generate` es una
> función de su **web app**, no expuesta en la API OpenAI-compatible documentada.
> Si en el futuro publican `/v1/images/generations`, la sección *Generar imágenes*
> de MaestroAI ya está lista para usarla (usa la ruta estándar de OpenAI).

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
- **Agents** (Hermes): agente conversacional en microVM (QEMU+KVM, disco ext4 20 GiB
  persistente, root) conectado a Telegram. 1 agente por miembro. Console web, subida
  de ficheros, observabilidad, exposición HTTP en `*.apps.nan.builders`.
- **Apps**: despliegue desde GitHub (Dockerfile en la raíz) dentro de un **Space**
  (cuota CPU/RAM/disco). Tiers Basic/Medium/Large; Basic gratis con la suscripción de
  inferencia. Auto-deploy en cada push; dominio público con HTTPS.

---

## Qué usa MaestroAI de NaN hoy
- ✅ **Chat / generación** (ruta `open`) → `qwen3.6` por defecto (compatible OpenAI).
  Es el modelo barato de la **cascada** y de la **condensación** de contexto.
- ✅ **rerank** (Qwen3-Reranker vía `/rerank`) → reordena el RAG para más precisión
  (embedding → rerank → LLM). Toggle en *Admin → Eficiencia de tokens*.
- 🔜 **Candidatos de alto valor** (endpoints reales de NaN, aún sin cablear):
  - **TTS (kokoro)** → narrar salidas en español; **STT (whisper)** → transcribir audio.
  - **embeddings (qwen3-embedding)** → fuente de embeddings del RAG.
- ⏳ **Imágenes**: la sección *Generar imágenes* está lista (ruta OpenAI estándar)
  pero **requiere un proveedor que exponga `/images/generations`** — la API de NaN
  no lo documenta hoy.
