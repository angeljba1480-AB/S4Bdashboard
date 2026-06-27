# Bitácora de cambios — MaestroAI

Formato basado en *Keep a Changelog*. Las versiones se promueven **dev → qa → main (prod)**.

## [No liberado]
- **Agente · function-calling nativo (qwen3.6)**: cuando hay un proveedor con
  *tool calling* (NaN qwen3.6), el planner deja de parsear JSON de prosa y usa
  **functions** reales — el modelo elige la herramienta y rellena los argumentos de
  forma fiable. Las acciones/workflows se exponen como `tools` (nombres saneados); el
  encadenamiento `{{stepN}}` se conserva en los argumentos. Fallback a texto-JSON y a
  heurística si el proveedor no soporta tools. `source: "modelo (tools)"`.
- **Imágenes NaN reales (`flux-2-klein`)**: NaN ya expone `/v1/images/generations` y
  `/v1/images/edits`. Se corrige el id del modelo (`flux-2-klein`, antes `FLUX.2-klein`
  → 404) y se deja de reutilizar el modelo de chat (qwen3.6) para imágenes — ahora hay
  un `settings.image_model` dedicado. *Generar imágenes* funciona end-to-end con una key
  de tier *inference*. Contexto del proveedor actualizado (`docs/PROVEEDOR-NAN.md`).
- **Confirmado: NaN no entrena (sin GPU para LoRA)**: el reference completo de la API no
  expone fine-tuning, y las microVM de *Agents* son CPU-only (1 vCPU/2 GiB). El
  fine-tuning se queda en infra del cliente (lab MLX / GPU externa). Documentado.
- **Agente · previsualización (dry-run) y recetas guardadas**: el *Asistente de acciones*
  ahora tiene **Previsualizar** (muestra el plan **sin ejecutar ni guardar nada**) además
  de Ejecutar, y permite **guardar una instrucción como receta** (playbook) para
  re-ejecutarla a demanda (`/actions/playbooks` CRUD + `/playbooks/{id}/run?dry_run=`).
  Útil para comandos multi-paso recurrentes («Cierre semanal: lee la hoja X, resume y
  publica en Teams»). El endpoint `/actions/agent` acepta `dry_run`.
- **Autochequeo del sistema (readiness + guía de arreglo)**: `GET /admin/readiness`
  revisa qué está configurado (modelo abierto/premium, on-prem, n8n, toolkit conectado,
  antivirus, OCR, trainer de fine-tuning, MFA, cifrado) y, **por cada hueco, devuelve la
  guía de cómo resolverlo ahí mismo** (pasos + enlace a la sección). Panel *Autochequeo
  del sistema* arriba en *Admin* con estados (listo / por configurar / falta) y arreglo
  expandible.
- **Agente de acciones · workflows n8n + encadenamiento**: el agente ahora también puede
  **disparar workflows de n8n** (`workflow:<id>` del catálogo) y **encadenar pasos** — la
  salida de un paso alimenta al siguiente vía `{{stepN}}` (p. ej. *buscar en SharePoint →
  resumir → publicar en Teams* en una sola orden). Triggers de workflow auditados y con
  aprobación como las escrituras.
- **Agente de acciones (el modelo ejecuta los pasos en las herramientas)**: nuevo
  `POST /actions/agent` + panel *Asistente de acciones* en la sección Acciones. Escribes
  una instrucción en lenguaje natural y el modelo la traduce a pasos del toolkit
  (Google/Microsoft) y los ejecuta **por detrás**: lecturas al momento; escrituras con
  **aprobación humana** (o «Permitir siempre» / ejecución directa con `auto_approve`).
  Planner modelo-primero con **fallback heurístico** (funciona en laboratorio sin modelo).
  Todo auditado (`agent_run`). Reusa la gobernanza de aprobaciones existente.
- **Catálogo de modelos de la industria para LoRA**: `MLX_MODEL_MAP` ampliado a las
  familias Llama (3/3.1/3.2/3.3), Mistral/Mixtral, Qwen (2.5/3 + Coder), Gemma (2/3),
  Phi (3/3.5/4), DeepSeek-R1 (distill) y otros (SmolLM2, Yi) → su id `mlx-community`.
  Nuevo `GET /finetune/base-models` y **selector agrupado por familia** en el panel de
  Fine-tuning (antes era texto libre).
- **Workflow n8n importable + wrapper** (`integrations/n8n/`): `lora-trainer.workflow.json`
  (Webhook → ejecuta el trainer → responde) y `lora-train-wrapper.sh` (mapea el payload de
  MaestroAI a `train-lora.sh`/`fuse-lora.sh` y hace el callback). README de puesta en marcha.

## 2026-06-27 — promovido a prod (PR #35 → #36)
- **Trainer LoRA alineado con el laboratorio MLX**: `dispatch_training` arma el payload
  que consume el wrapper de `train-lora.sh` + `fuse-lora.sh` (Apple Silicon/MLX-LM):
  `mlx_model` (vía `MLX_MODEL_MAP`: Llama-3.2-3B / Llama-3.1-8B / DeepSeek-R1-8B),
  `train_jsonl`/`valid_jsonl` (MLX-LM exige ambos), `ollama_name` e `hyperparams`
  (ITERS/BATCH/LR/NUM_LAYERS configurables). El callback reporta `serve_base_url`
  (Ollama por túnel) + `metrics.served_model`. `docs/FINETUNING-SETUP.md` incluye el
  payload y el wrapper bash que mapea a las env vars del lab.
- **Integración on-prem (modelos locales del cliente)**: las rutas **local (Ollama)** y
  **VPC** ahora se configuran como conectores desde *Admin → Modelos y conectores* (Base
  URL + modelo + key + **Probar conexión**), no solo por variables de entorno. Pensado para
  conectar el laboratorio/infra local del cliente (Ollama/vLLM/Qdrant/n8n) vía túnel o
  despliegue on-prem. Guía `docs/ONPREM-LAB.md` + ayuda contextual.
- **Panel de Fine-tuning en la UI**: sección *Fine-tuning* que explica el beneficio de
  cada paso (reunir ejemplos → desde Memoria → gate calidad/red-team → entrenar LoRA →
  servir privado), con creación de datasets, ejemplos, import desde Memoria, gate, export
  JSONL y lanzamiento/seguimiento de jobs. Ayuda contextual incluida.
- **Fine-tuning ligero (LoRA) — andamiaje** (Fase 5 del blueprint): datasets versionados
  con **anonimización** de PII, **gate de calidad/red-team**, export JSONL y **jobs** que
  se despachan a un *trainer* externo con GPU (servidor / App NaN / webhook n8n) o quedan
  `simulado` (modo laboratorio). Callback para reportar el adapter y servirlo como ruta
  local/VPC (Ollama/vLLM). Guía: `docs/FINETUNING-SETUP.md`. Endpoints `/finetune/*`.
- **MFA (verificación en dos pasos · TOTP)**: enrolamiento (app autenticadora) +
  **códigos de respaldo** de un solo uso; el login exige el código cuando MFA está
  activo. Secreto TOTP cifrado. Endpoints `/auth/mfa/setup|verify|disable`; UI en
  *Mi cuenta* y en el login. (Solo se exige si hay secreto enrolado → sin lockout.)
- **OCR de escaneados**: el binario **tesseract + poppler** se instala en la imagen
  (Dockerfile) y se activan `pytesseract`/`pdf2image`; los PDFs sin capa de texto se
  pasan por OCR en la ingesta.
- **Antivirus en la ingesta**: al subir un archivo se escanea antes de procesarlo —
  firma estándar **EICAR** (determinista, sin infra) + **ClamAV opcional** si hay daemon,
  con **tope de tamaño** configurable. Los archivos infectados/grandes se **rechazan
  (422) y auditan** (`ANTIVIRUS_ENABLED`, `CLAMAV_HOST/PORT/SOCKET`, `MAX_UPLOAD_MB`).
- **Ayuda contextual (popup por sección)**: cada sección tiene un botón **? Ayuda** en
  el encabezado que abre un **popup** con la guía relevante (pasos + notas) y enlace a la
  Ayuda completa. Contenido compartido en `lib/help.ts`.
- **Documentación generada**: `docs/generados/MaestroAI-Documentacion.docx` (documento
  completo) y `MaestroAI-Presentacion.pptx` (presentación ejecutiva).
- **Enrutamiento NaN-primero**: los datos no sensibles **siempre empiezan con NaN
  (open)**; premium dejó de ser ruta base y ahora es **escalada a demanda** (toggle
  «máxima precisión») o automática **si la respuesta es insuficiente**. El banner del
  chat muestra la ruta real (ya no “promete” premium). Si no hay premium configurado,
  todo corre en NaN; si tampoco hay NaN, modo demostración (mock).
- **Ayuda en español (in-app)**: nueva sección *Ayuda* con guías paso a paso
  (conectar **n8n**, correo, documentos/RAG, acciones Google/MS, conectores, importar
  BD/CSV, modelos/cascada/rerank, imágenes, webhooks). Buscador + banner desde
  Integraciones.
- **Reranking del RAG (NaN)**: tras recuperar por embeddings, reordena los candidatos
  con el reranker (Qwen3-Reranker vía `/rerank`) para más precisión (embedding → rerank
  → LLM). Toggle en *Admin → Eficiencia de tokens*; usa el proveedor abierto. Si el
  reranker falla, cae al orden por coseno.
- **Generación de imágenes (texto→imagen)**: nueva sección *Generar imágenes* (ruta
  estándar OpenAI `/images/generations` sobre el proveedor abierto). Prompt con
  redacción de PII, relación de aspecto (1:1/16:9/9:16) y variantes (1–4). Galería por
  área, copia almacenada y auditada (`/images/*`). Nota: la API de NaN no expone
  imágenes hoy (su *Generate* es web) — ver `docs/PROVEEDOR-NAN.md`.
- **Contexto del proveedor NaN** (`docs/PROVEEDOR-NAN.md`): referencia de su API
  compatible OpenAI (endpoints, modelos, rate limits) y productos (Agents, Apps).
- **Conectores · detalles + "ojito"**: ver qué se configuró (endpoint, header, ejemplo
  de payload por tipo) y revelar el secreto/DSN con un ojo (solo ADMIN/DEVOPS, auditado):
  `GET /integrations/connectors/{id}/reveal` y `GET /datasources/{id}/reveal`.
- **Toolkit · Excel y SharePoint**: leer rango de Excel y **agregar fila a tabla**
  (Graph workbook), **buscar en SharePoint**. Nuevos scopes `Files.ReadWrite.All`
  y `Sites.Read.All` (la escritura sigue con aprobación humana).
- **Conector CSV** para sistemas legados sin API: importa un CSV pegado al
  repositorio + RAG (`/datasources/import-csv`), con panel en Integraciones.
- **Verificar modelo premium**: botón *Probar conexión* (Admin → Modelos externos)
  y endpoint `POST /admin/providers/{route}/test` que hace una llamada real mínima
  al proveedor y reporta ok + latencia + muestra (o el error), auditado.

## 2026-06-25 — promovido a prod (PR #12)
- CI: primera corrida en `dev`/`qa` para registrar los checks (`API · pytest`,
  `Web · build`) y validar la compuerta antes de producción.
- **Eficiencia de tokens en la UI**: controles de condensación y tope de gasto por
  consulta configurables (Admin), con ahorro acumulado.
- **Toolkit · lecturas**: Google Sheets, Google/Outlook Calendar y OneDrive.
- **Conector de base de datos** (solo lectura) → importa al RAG (`/datasources`).
- **Frontend** de fuentes de datos en Integraciones.
- **Seguridad**: revisión del código nuevo + fixes — config global restringida a
  super admin, sanitización de consultas Drive/OneDrive, denylist DML/CTE y
  esquemas de DSN permitidos, escapado de segmentos de URL en acciones.

## 2026-06-25

### Añadido
- **Memoria + Tags** (#6): memoria persistente por usuario, búsqueda semántica +
  por tags, auto-captura al completar casos, recall en el chat (`use_memory`),
  página *Memoria*.
- **Eficiencia de tokens** (#5): condensación del contexto con el modelo barato
  antes de premium, escalado por respuesta insuficiente, tope de tokens por
  consulta (`MAX_TOKENS_PER_REQUEST`).
- **Toolkit de acciones Google/Microsoft** (#... Sprint 7): enviar correo, crear
  eventos, append a Sheets, publicar en Teams; aprobación humana + "Permitir
  siempre".
- **Scopes de escritura** y guía `ACCIONES-ESCRITURA-SETUP.md` (#3).
- **Notebooks** (estilo NotebookLM), **LLMs externos** configurables y **cascada
  de modelos** (Sprint 6).
- **Dashboard reforzado + auditoría navegable** (Sprint 5).
- **Salidas** PPTX/XLSX, **reportes por industria** y **Google Drive** como
  contexto (Sprint 4).
- **Flujogramas navegables** (Sprint 3).
- **Gobernanza**: super admin + permisos por área y licencia (Sprint 2).
- **Línea base**: onboarding obligatorio + paso objetivo/notas/formato (Sprint 1).
- **Documentos por área + categorías + tratamiento**, **chat con 3 modos de
  contexto**, **recetas con grounding por categoría**, **multi-cuenta de correo**.
- **Diagramas de arquitectura** (`docs/ARQUITECTURA.md`) y **modelo de entornos**
  (`docs/ENTORNOS.md`).

### Corregido
- Build de Vercel: el tipo de `api.chat` no incluía `precision`/`approve_external`
  (rompía TypeScript). Verificado con `tsc` y `next build` (#6).

### Seguridad / privacidad
- Redacción de PII antes de cualquier salida externa; credenciales cifradas
  (AES-256-GCM); todo auditado; permisos por área aplicados en documentos, chat,
  recetas, notebooks y memoria.

---

> Cómo registrar cambios: agrega tu entrada bajo **[No liberado]** al abrir el PR
> a `qa`; al promover a `main` se fecha y se mueve a una sección de versión.
