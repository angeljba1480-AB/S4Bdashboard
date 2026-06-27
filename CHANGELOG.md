# Bitácora de cambios — MaestroAI

Formato basado en *Keep a Changelog*. Las versiones se promueven **dev → qa → main (prod)**.

## [No liberado]
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
