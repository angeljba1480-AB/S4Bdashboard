# Estado del proyecto — MaestroAI

> Bitácora viva de lo construido, cómo se despliega y qué falta. Última
> actualización: 2026-06-25.

Plataforma de **AI privada y gobernada** (Private AI Gateway + agentes
verticales): los datos se clasifican, la PII se redacta y el enrutador de
privacidad decide local / VPC / abierto / premium / bloqueo — todo auditado.

---

## 1. Arquitectura de despliegue

| Componente | Plataforma | URL |
|---|---|---|
| Portal (Next.js) | **Vercel** | (dominio del portal / `plataforma.maestroai.mx`) |
| API (FastAPI) | **Render** | `https://s4bdashboard.onrender.com` |
| Base de datos | Postgres (Render/Supabase) | — |
| Repo | GitHub `angeljba1480-AB/S4Bdashboard`, rama `main` | — |

> Cada push a `main` dispara **dos** despliegues independientes (Vercel + Render).
> Si el portal nuevo llama a una API vieja, revisar que Render redeployó desde `main`.

---

## 2. Funcionalidades (estado)

### Correo y cuentas
- ✅ Conexión OAuth **Outlook / Gmail** + **IMAP** (Yahoo, iCloud, Zoho, hosting…).
- ✅ **Varias cuentas por proveedor** (personal + trabajo); selector de cuenta.
- ✅ Caso «Resumen de correo y agenda».

### Documentos y RAG
- ✅ Repositorio por **área** + **catálogo de categorías** extensible.
- ✅ **Tratamiento** (público/interno/confidencial/restringido) auto-detectado y editable.
- ✅ Borrar y **re-etiquetar**; índice RAG cifrado.
- ✅ **Google Drive** como contexto (importar archivos al RAG).
- ✅ **Ingesta**: extrae texto de **PDF/DOCX** + **OCR** de escaneados (tesseract en la
  imagen) y **antivirus** en la subida (EICAR + ClamAV opcional + tope de tamaño).
- ✅ **MFA (TOTP)**: verificación en dos pasos con códigos de respaldo; exigida en login.
- ✅ **Fine-tuning LoRA (andamiaje + panel UI)**: datasets anonimizados + gate de
  calidad/red-team + export JSONL + jobs hacia un trainer con GPU (o `simulado`).
  **Panel en el portal** que explica el beneficio de cada paso. Ver `FINETUNING-SETUP.md`.

### Casos de uso (recetas)
- ✅ Paso universal **objetivo / notas / formato** de salida.
- ✅ **Grounding por categoría** (cada caso jala de su tipo de documento).
- ✅ **Reporte por industria** (plantillas por sector).
- ✅ Export a **PDF / Word / Markdown / PPTX / XLSX**.

### Chat y Notebooks
- ✅ Chat con **3 modos de contexto** (sin contexto / todo / elegir documentos).
- ✅ **Notebooks** (estilo NotebookLM): fuentes + preguntas citadas + artefactos
  (resumen, FAQ, guía, briefing, cronología).

### Imágenes (texto → imagen)
- ✅ **Generar imágenes** vía la ruta estándar OpenAI `/images/generations` sobre el
  proveedor abierto. Prompt con redacción de PII, relación de aspecto y variantes.
  **Galería por área**, copia almacenada y auditada.
  ✅ **NaN ya expone imágenes** (`flux-2-klein`, tier *inference*): MaestroAI usa
  `settings.image_model = flux-2-klein` (distinto del modelo de chat). Ver
  [`PROVEEDOR-NAN.md`](./PROVEEDOR-NAN.md).

### Modelos
- ✅ **Router de privacidad** con redacción de PII y fallback.
- ✅ **Reranking del RAG** (NaN `/rerank`): reordena los candidatos recuperados para
  más precisión (embedding → rerank → LLM). Toggle en *Admin → Eficiencia de tokens*.
- ✅ **Modelos externos** (GPT/Claude/Llama/DeepSeek) configurables en la UI
  (cifrados; endpoints compatibles con OpenAI).
- ✅ **Integración on-prem**: rutas **local (Ollama)** y **VPC** configurables como
  conectores en la UI (Probar conexión) para usar la infra local del cliente. Ver
  `ONPREM-LAB.md`.
- ✅ **Cascada (NaN-primero)**: los datos no sensibles empiezan en NaN (open);
  premium es **escalada a demanda** («máxima precisión») o automática si la respuesta
  es insuficiente (aprobación para contenido sensible). Si no hay premium, se queda
  en NaN; sin NaN, modo demostración.
- ✅ **Eficiencia de tokens**: antes de pagar premium, el contexto grande (PDFs)
  se **condensa con el modelo barato** (NaN/open) → premium recibe un extracto
  chico. Escala a premium si la respuesta del barato **es insuficiente**.
  **Tope de tokens por consulta** configurable (`MAX_TOKENS_PER_REQUEST`).

### Toolkit de acciones (Google/Microsoft)
- ✅ Enviar correo, crear eventos, append a Sheets, publicar en Teams,
  **agregar fila a tabla de Excel**.
- ✅ **Lecturas**: Google Sheets, Google/Outlook Calendar, OneDrive,
  **leer rango de Excel**, **buscar en SharePoint**.
- ✅ **Aprobación humana** para escrituras + **“Permitir siempre”** (revocable).
- ✅ **Agente de acciones**: el modelo traduce una instrucción en lenguaje natural a
  pasos del toolkit y los **ejecuta por detrás** (lecturas al momento; escrituras con
  aprobación). `POST /actions/agent` + panel *Asistente* (planner modelo + heurística).
  Puede **disparar workflows n8n** y **encadenar pasos** (`{{stepN}}`: la salida de uno
  alimenta al siguiente). **Previsualización (dry-run)** antes de ejecutar y **recetas
  guardadas** (playbooks) re-ejecutables. Con NaN (qwen3.6) usa **function-calling
  nativo**; sin modelo, cae a heurística.

### Ayuda
- ✅ **Ayuda in-app en español**: guías paso a paso (n8n, correo, RAG, acciones,
  conectores, BD/CSV, modelos/rerank, imágenes, webhooks) con buscador.
- ✅ **Ayuda contextual por sección**: botón *? Ayuda* en cada encabezado abre un
  **popup** con la guía relevante (no solo el menú).
- ✅ **Documentación** en Word y PowerPoint en `docs/generados/`.

### Gobernanza y visibilidad
- ✅ **Autochequeo del sistema**: *Admin* revisa qué falta (modelos, n8n, toolkit,
  antivirus, OCR, trainer, MFA, cifrado) y muestra **la guía de cómo resolver cada
  hueco ahí mismo**. `GET /admin/readiness`.
- ✅ **Super admin** (ve todos los tenants) + **permisos por área y licencia**.
- ✅ **Flujogramas navegables** (los 3 base del blueprint + flujo de caso + libre).
- ✅ **Dashboard** reforzado + **auditoría navegable** (filtros, búsqueda, detalle, stats).

---

## 3. Configuración pendiente del cliente (fuera del código)

Para activar lo que depende de credenciales/permisos:

1. **Scopes de escritura** (toolkit de acciones): agregar permisos en Azure/Google
   y **reconectar** — ver [`ACCIONES-ESCRITURA-SETUP.md`](./ACCIONES-ESCRITURA-SETUP.md).
2. **Modelo Premium** para la cascada: *Admin → Modelos externos* (Base URL + modelo + API key).
   Luego pulsa **Probar conexión** para verificar que responde (latencia + muestra).
3. **Google Drive**: reconectar Google para otorgar `drive.readonly`.
4. Verificar que **Render** despliega desde `main` (Branch = `main`).

---

## 4. Calidad

- ✅ **222 pruebas** automatizadas en verde (API).
- Migraciones aditivas idempotentes (sin pérdida de datos).
- Credenciales cifradas (AES-256-GCM); todo auditado.

---

## 5. Pendientes / backlog

### 🔜 Próximo sprint: Memoria + Tags (recordar trabajos)
Para poder decir *"¿recuerdas el trabajo C?"* y que el sistema recupere lo hecho.
- [ ] **Memoria persistente**: guardar resultados/respuestas (chat, casos, notebooks)
  como elementos de memoria recuperables.
- [ ] **Tags** estilo gestor de contenido para organizar y filtrar el trabajo.
- [ ] **Recall en RAG**: incluir la memoria en la recuperación (responder con base
  en trabajos previos), respetando permisos por área.
- [ ] UI: "Mis trabajos / Memoria" con búsqueda por tag y "continuar este trabajo".

### Hecho recientemente (trabajo autónomo en `dev`)
- ✅ **Tope de gasto + eficiencia en la UI** (Admin → Eficiencia de tokens) + ahorro acumulado.
- ✅ **Lecturas del toolkit**: Google Sheets, Google/Outlook Calendar, OneDrive.
- ✅ **Conector de base de datos** (solo lectura) → importa al RAG (`/datasources`).
- ✅ **Revisión de seguridad** del código nuevo + fixes (authz global solo super
  admin, sanitización de queries Drive/OneDrive, denylist DML/CTE + esquemas DSN,
  escapado de URLs en acciones).
- ✅ **Excel (Graph workbook)** lectura de rango + agregar fila a tabla; **SharePoint
  search** (scopes `Files.ReadWrite.All` + `Sites.Read.All`).
- ✅ **Importar CSV** de sistemas legados → repositorio + RAG (`/datasources/import-csv`),
  con panel en Integraciones.
- ✅ **Verificación del modelo premium**: botón *Probar conexión* (Admin → Modelos
  externos) → `POST /admin/providers/{route}/test` hace una llamada real mínima y
  reporta ok + latencia + muestra, o el error (auditado). Distingue MOCK de proveedor real.

### Otras ideas (candidatas)
- **SFTP** para sistemas legados (requiere `paramiko`).
- Centrar integraciones a medida en **n8n** (catálogo de recetas: DB, SOAP, apps propias).

_MaestroAI · Estado del proyecto._
