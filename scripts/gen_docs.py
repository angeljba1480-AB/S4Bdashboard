"""Documentación EXTENSA de MaestroAI → Word (.docx) y PowerPoint (.pptx)."""
from __future__ import annotations

import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt, RGBColor, Inches
from pptx import Presentation
from pptx.util import Inches as PInches, Pt as PPt
from pptx.dml.color import RGBColor as PColor

OUT = os.environ.get("OUT_DIR", ".")
VIOLET = RGBColor(0x6D, 0x28, 0xD9)
SLATE = RGBColor(0x33, 0x41, 0x55)
GREY = RGBColor(0x64, 0x74, 0x8B)
PV = PColor(0x6D, 0x28, 0xD9); PW = PColor(0xFF, 0xFF, 0xFF)
PS = PColor(0x33, 0x41, 0x55); PG = PColor(0x64, 0x74, 0x8B)

# ============================================================ DATA (appendices)
ENDPOINTS = {
    "Autenticación / cuenta": ["POST /auth/login", "GET /me", "GET /account", "GET /auth/sso/config", "GET /auth/sso/callback"],
    "Chat y casos": ["POST /chat", "POST /chat/preview", "GET/POST /recipes", "POST /recipes/{id}/start",
                      "POST /recipes/runs/{id}/approve", "POST /recipes/runs/{id}/export", "POST /v1/cases/{recipe_id}/run"],
    "Documentos y RAG": ["GET/POST /documents", "POST /documents/upload", "GET/POST /documents/categories",
                          "DELETE /documents/{id}", "GET /drive/files", "POST /drive/import"],
    "Notebooks / Memoria": ["GET/POST /notebooks", "POST /notebooks/{id}/ask", "POST /notebooks/{id}/generate/{kind}",
                            "GET/POST /memory", "GET /memory/tags", "DELETE /memory/{id}"],
    "Imágenes": ["GET /images/config", "POST /images/generate", "GET /images", "GET /images/{id}/data", "DELETE /images/{id}"],
    "Acciones (toolkit)": ["GET /actions", "POST /actions/run", "GET /actions/requests",
                           "POST /actions/requests/{id}/approve", "POST /actions/requests/{id}/reject", "GET/DELETE /actions/grants"],
    "Integraciones": ["GET/POST /integrations/connectors", "POST /integrations/connectors/{id}/test",
                      "GET /integrations/connectors/{id}/reveal", "GET/POST /integrations/webhooks",
                      "GET/POST /datasources", "POST /datasources/import-csv", "POST /datasources/{id}/import",
                      "GET /datasources/{id}/reveal", "POST /oauth/{provider}/authorize", "POST /oauth/imap"],
    "Automatizaciones / workflows": ["GET/POST /automations", "POST /automations/from-template",
                                     "POST /automations/{id}/run", "POST /automations/run-due", "GET /flowcharts"],
    "Admin / gobierno": ["GET/PUT /admin/providers", "POST /admin/providers/{route}/test", "GET/PUT /admin/efficiency",
                         "GET /admin/routes", "GET /admin/security", "GET/POST /admin/users", "GET /admin/tenants",
                         "GET /admin/billing", "GET/POST /admin/api-keys", "GET /admin/n8n"],
    "Auditoría / uso / salud": ["GET /audit", "GET /audit/export", "GET /audit/stats", "GET /usage", "GET /health",
                                "POST /v1/events", "POST /v1/webhooks/{id}"],
}

ACTIONS = [
    ("gmail.send", "Google", "Sí", "to, subject, body"),
    ("gcal.create_event", "Google", "Sí", "summary, start, end, location"),
    ("gsheets.append", "Google", "Sí", "spreadsheet_id, range, values"),
    ("gsheets.read", "Google", "No", "spreadsheet_id, range"),
    ("gcal.list", "Google", "No", "days"),
    ("outlook.send", "Microsoft", "Sí", "to, subject, body"),
    ("mscal.create_event", "Microsoft", "Sí", "summary, start, end, location"),
    ("teams.post", "Microsoft", "Sí", "team_id, channel_id, message"),
    ("excel.append", "Microsoft", "Sí", "item_id, table, values"),
    ("mscal.list", "Microsoft", "No", "days"),
    ("onedrive.list", "Microsoft", "No", "query"),
    ("excel.read", "Microsoft", "No", "item_id, worksheet, range"),
    ("sharepoint.search", "Microsoft", "No", "query"),
]

ENVVARS = [
    ("SECRET_KEY", "Núcleo", "Clave de firma JWT (32+ caracteres)."),
    ("DATABASE_URL", "Núcleo", "Postgres (Supabase Session Pooler). Sin ella, SQLite efímero."),
    ("CORS_ORIGINS / CORS_ORIGIN_REGEX", "Núcleo", "Orígenes permitidos del portal."),
    ("APP_ENV", "Núcleo", "production / development."),
    ("OPEN_ENABLED / OPEN_API_KEY / OPEN_BASE_URL / OPEN_MODEL", "Modelos", "Ruta abierta — NaN Builders."),
    ("PREMIUM_ENABLED / PREMIUM_API_KEY / PREMIUM_BASE_URL / PREMIUM_MODEL", "Modelos", "Ruta premium (OpenAI/Claude/Gemini compatible)."),
    ("LOCAL_ENABLED / LOCAL_BASE_URL / LOCAL_MODEL", "Modelos", "Ruta local (Ollama)."),
    ("VPC_ENABLED / VPC_BASE_URL / VPC_API_KEY / VPC_MODEL", "Modelos", "Ruta VPC (vLLM/TGI)."),
    ("ALLOW_CLOUD_FALLBACK", "Modelos", "Permite subir a nube si la ruta privada no tiene modelo real (opt-in)."),
    ("CONDENSE_ENABLED / CONDENSE_THRESHOLD_CHARS / MAX_TOKENS_PER_REQUEST", "Eficiencia", "Condensación + tope de gasto."),
    ("RERANK_ENABLED / RERANK_MODEL / RERANK_CANDIDATES", "Eficiencia", "Reranking del RAG (NaN)."),
    ("ENCRYPTION_ENABLED / MASTER_KMS_KEY / KMS_KEY_VERSION", "Seguridad", "Cifrado en reposo AES-256-GCM."),
    ("VECTOR_STORE / QDRANT_URL / QDRANT_API_KEY", "RAG", "inprocess (default) o qdrant."),
    ("EMBEDDINGS_PROVIDER / EMBEDDINGS_MODEL / EMBEDDINGS_DIM", "RAG", "Fuente de embeddings."),
    ("N8N_ENABLED / N8N_WEBHOOK_BASE_URL / N8N_API_BASE_URL / N8N_API_KEY / N8N_AUTO_PROVISION", "Workflows", "Integración n8n gestionada."),
    ("MICROSOFT_* / GOOGLE_*", "OAuth", "Client id/secret/redirect + scopes de correo y acciones."),
    ("SSO_ENABLED / OIDC_*", "SSO", "Inicio de sesión federado opcional."),
    ("NEXT_PUBLIC_API_BASE_URL", "Frontend (Vercel)", "URL pública del backend (sin / final)."),
]

NAN_MODELS = [
    ("qwen3.6", "MoE 35B/3B", "256K", "Chat, tools, visión, reasoning — principal"),
    ("deepseek-v4-flash", "MoE 284B/21B", "1M", "Chat, tools, reasoning (reasoning_effort)"),
    ("mimo-v2.5", "MoE 310B/15B", "1M", "Omnimodal (texto+imagen+audio), tools, reasoning"),
    ("gemma4", "MoE 26B/4B", "256K", "Chat, visión, reasoning (opt-in)"),
    ("qwen3-embedding", "8B", "—", "Embeddings 4096-dim, 100+ idiomas"),
    ("rerank", "Qwen3-Reranker-8B", "—", "Reranking RAG (/rerank)"),
    ("kokoro", "TTS 82M", "—", "Text-to-speech, voces ES"),
    ("whisper", "large-v3", "—", "Speech-to-text, 99+ idiomas"),
]

MODULES = [
    ("Casos de uso (recetas)", "Genera entregables (propuestas, cartas, reportes, licitaciones) con un paso universal objetivo/notas/formato y grounding por categoría. Borrador → aprobar → exportar a Word/PDF/Markdown/PPTX/XLSX. Reporte por industria con plantillas por sector."),
    ("Agentes verticales", "Agentes especializados (Document Intelligence, Cyber Diagnostic, Proposal/SOW, Executive Copilot) configurables por área; cada respuesta pasa por el router de privacidad y cita fuentes."),
    ("Chat con fuentes", "3 modos de contexto (sin contexto / todo el RAG / elegir documentos), toggles de máxima precisión (cascada) y memoria; banner con clasificación y ruta real; exportable."),
    ("Notebooks", "Estilo NotebookLM privado: fuentes + preguntas citadas + artefactos (resumen, FAQ, guía, briefing, cronología) acotados a esos documentos."),
    ("Documentos y RAG", "Repositorio por área + catálogo de categorías; tratamiento auto-detectado (público/interno/confidencial/restringido) y editable; borrar y re-etiquetar; Drive como contexto; índice cifrado."),
    ("Memoria y etiquetas", "Memoria persistente de trabajos con búsqueda semántica + por tags; recall en el chat ('¿recuerdas el trabajo C?'); auto-captura al completar casos."),
    ("Generar imágenes", "Texto→imagen (ruta estándar OpenAI), relación de aspecto y variantes; galería por área; PII redactada; auditada."),
    ("Flujogramas", "La lógica del producto navegable: los flujos base del blueprint + flujo de caso + diseño libre."),
    ("Tableros", "Dashboards a la medida: describe qué medir, agrega KPIs y gráficas en vivo (tokens por fuente, casos por receta, costo por ruta) + KPIs manuales."),
    ("Trámites y casos (MCP)", "Catálogo curado por país/estado/empresa por ejes de desarrollo; convierte un trámite en propuesta de caso; aterriza (grounding) las respuestas."),
    ("App Studio", "Construye mini-apps con IA y publícalas (pago por despliegue)."),
    ("Automatizaciones", "Disparador (manual/programado/evento) → acción (workflow n8n / caso / conector / notificar), con plantillas y ejecución manual."),
]


# ===================================================================== WORD
def build_docx(path: str) -> None:
    doc = Document()
    base = doc.styles["Normal"]; base.font.name = "Calibri"; base.font.size = Pt(10.5)
    for i, sz in ((1, 18), (2, 14), (3, 12)):
        st = doc.styles[f"Heading {i}"]; st.font.color.rgb = VIOLET; st.font.size = Pt(sz)

    def para(text, bold=False, color=SLATE, size=10.5, italic=False):
        p = doc.add_paragraph(); r = p.add_run(text); r.bold = bold; r.italic = italic
        r.font.color.rgb = color; r.font.size = Pt(size); return p

    def bullets(items):
        for it in items:
            p = doc.add_paragraph(style="List Bullet")
            if isinstance(it, tuple):
                r = p.add_run(it[0] + ": "); r.bold = True; p.add_run(it[1])
            else:
                p.add_run(it)

    def table(headers, rows):
        t = doc.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.style = "Light Grid Accent 1"
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i].paragraphs[0].add_run(h); c.bold = True; c.font.size = Pt(9.5)
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                rp = cells[i].paragraphs[0].add_run(str(v)); rp.font.size = Pt(9)
        doc.add_paragraph()

    # ---- Cover
    sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for _ in range(4):
        doc.add_paragraph()
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("MaestroAI"); r.bold = True; r.font.size = Pt(46); r.font.color.rgb = VIOLET
    st = doc.add_paragraph(); st.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = st.add_run("Documentación técnica y funcional"); r.font.size = Pt(20); r.font.color.rgb = SLATE
    su = doc.add_paragraph(); su.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = su.add_run("Plataforma de IA privada y gobernada (Private AI Gateway + agentes verticales)")
    r.font.size = Pt(12); r.font.color.rgb = GREY
    dt = doc.add_paragraph(); dt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dt.add_run("Versión 2026 · Documento confidencial").italic = True
    doc.add_page_break()

    # ---- 1. Introducción
    doc.add_heading("1. Introducción y propuesta de valor", level=1)
    para("MaestroAI no es «otro ChatGPT»: es una capa privada y gobernada sobre la IA, "
         "pensada para empresas de LATAM que necesitan aprovechar modelos de lenguaje sin "
         "exponer datos sensibles ni perder control ni trazabilidad. El diferenciador central "
         "es el Enrutador de Privacidad (Privacy Model Router): por cada dato que se procesa, la "
         "plataforma clasifica su sensibilidad, detecta PII, minimiza y redacta, y decide "
         "automáticamente la ruta del modelo (local, VPC, abierto o premium) o lo bloquea — todo auditado.")
    para("Sobre esa base corren capacidades verticales: RAG documental por área, casos de uso que "
         "generan entregables, agentes especializados, notebooks, automatizaciones e integraciones "
         "con las herramientas que la empresa ya usa (Google Workspace, Microsoft 365, CRM/ERP, n8n).")
    doc.add_heading("Principios de diseño", level=2)
    bullets([
        ("Privacidad por defecto", "el usuario nunca elige el modelo; lo decide la política."),
        ("Trazabilidad total", "cada acción y ruteo queda auditado con su razón."),
        ("Costo bajo control", "NaN-primero, condensación de contexto y tope de gasto."),
        ("Gobernanza por área y licencia", "cada quien ve solo lo que le corresponde."),
        ("Extensible", "API pública, conectores, webhooks y n8n para todo lo demás."),
    ])

    # ---- 2. Glosario
    doc.add_heading("2. Glosario", level=1)
    table(["Término", "Definición"], [
        ["Tenant", "Una empresa/organización aislada dentro de la plataforma (multi-tenant)."],
        ["Router de privacidad", "Componente que clasifica y decide la ruta del modelo por cada petición."],
        ["RAG", "Retrieval-Augmented Generation: recuperar fragmentos relevantes y responder citándolos."],
        ["Rerank", "Reordenar candidatos del RAG por relevancia real con un cross-encoder."],
        ["Cascada", "Borrador con modelo barato (NaN) y refinamiento premium a demanda."],
        ["PII", "Información personal identificable (RFC, CURP, CLABE, tarjetas, correos, salud…)."],
        ["Ruta", "Destino de inferencia: local / VPC / open (NaN) / premium / bloqueado."],
        ["Área / Licencia", "Dimensiones de permisos: qué documentos y contexto ve cada usuario."],
    ])

    # ---- 3. Arquitectura
    doc.add_heading("3. Arquitectura general", level=1)
    para("La plataforma es un monorepo con dos despliegues independientes:")
    bullets([
        ("Portal (Next.js 15 + Tailwind)", "alojado en Vercel; PWA instalable."),
        ("API (FastAPI + SQLModel)", "alojada en Render (Docker); Postgres (Supabase) en producción."),
        ("Almacén vectorial", "in-process (por defecto) o Qdrant gestionado."),
        ("Modelos", "NaN (open), Ollama (local), vLLM/TGI (VPC), OpenAI/Claude/Gemini (premium)."),
        ("Workflows", "n8n gestionado (auto-provisión por tenant)."),
    ])
    doc.add_heading("Flujo de una petición (chat / caso)", level=2)
    bullets([
        "1. El portal envía el prompt + selección de contexto a la API.",
        "2. El RAG recupera fragmentos por embeddings (y los reordena con rerank si está activo).",
        "3. El router clasifica sensibilidad + PII y decide la ruta; minimiza y redacta el contexto.",
        "4. Se genera la respuesta en la ruta elegida (con fallback seguro si el proveedor falla).",
        "5. Cascada opcional: refina con premium a demanda o si la respuesta es insuficiente.",
        "6. Se persiste el mensaje, se cita la fuente y se registra el evento de auditoría.",
    ])

    # ---- 4. Privacidad y ruteo
    doc.add_heading("4. Modelo de privacidad y enrutamiento", level=1)
    para("El router implementa un árbol de decisión que prioriza la privacidad sobre el costo y la "
         "conveniencia. El usuario no interviene en la elección.")
    table(["Situación del dato", "Ruta", "Notas"], [
        ["Restringido", "Local", "Nunca sale de la infraestructura."],
        ["Confidencial", "VPC (o Local)", "VPC privada con auditoría; local si no hay VPC."],
        ["PII sin alta sensibilidad", "VPC / Local", "No sale a externo por defecto."],
        ["Interno / Público", "Open (NaN)", "Empieza en NaN; premium solo a demanda/insuficiencia."],
        ["Inyección / exfiltración", "Bloqueado", "Política de seguridad; se audita el intento."],
    ])
    para("NaN-primero: los datos no sensibles SIEMPRE empiezan con el modelo abierto (NaN). Premium "
         "no es ruta base; es una escalada que ocurre solo cuando el usuario pide «máxima precisión» o "
         "cuando la respuesta del modelo barato resulta insuficiente. Si no hay premium configurado, "
         "todo se resuelve en NaN; si tampoco hay NaN, la plataforma responde en modo demostración (mock) "
         "e invita a configurar un proveedor real. Datos sensibles nunca escalan a la nube sin aprobación.")

    # ---- 5. RAG
    doc.add_heading("5. RAG: ingesta, recuperación y citaciones", level=1)
    bullets([
        ("Ingesta", "el documento se clasifica (sensibilidad + PII), se trocea (chunking con solape) y se cifra."),
        ("Embeddings", "se calculan sobre texto plano; los fragmentos se almacenan cifrados (AES-256-GCM)."),
        ("Recuperación", "búsqueda vectorial acotada por tenant, categoría y áreas visibles del usuario."),
        ("Reranking", "opcional, reordena los candidatos por relevancia real (NaN Qwen3-Reranker)."),
        ("Citaciones", "cada respuesta indica documento, fragmento y score; respeta permisos por área."),
    ])

    # ---- 6. Cascada y eficiencia
    doc.add_heading("6. Cascada de modelos y eficiencia de tokens", level=1)
    para("Para controlar costo sin sacrificar calidad, la plataforma combina un modelo barato (NaN) con "
         "uno premium bajo demanda y reduce el tamaño de lo que se envía:")
    bullets([
        ("Condensación", "antes de pagar premium, el contexto grande se condensa con el modelo barato."),
        ("Tope de gasto", "MAX_TOKENS_PER_REQUEST limita los tokens por consulta (0 = sin tope)."),
        ("Escalada por insuficiencia", "si el borrador barato es pobre, se sube a premium automáticamente."),
        ("Ahorro acumulado", "el panel de Eficiencia muestra los tokens ahorrados."),
    ])

    # ---- 7. Módulos
    doc.add_heading("7. Módulos funcionales", level=1)
    for name, desc in MODULES:
        doc.add_heading(name, level=3)
        para(desc)

    # ---- 8. Integraciones
    doc.add_heading("8. Integraciones", level=1)
    bullets([
        ("Correo", "OAuth Outlook/Gmail + IMAP (Yahoo, iCloud, Zoho, hosting); varias cuentas por proveedor."),
        ("Google Drive", "importar archivos al RAG como contexto (scope drive.readonly)."),
        ("Conectores de salida", "CRM/ERP/Delivery (HubSpot, Salesforce, Shopify, Rappi, genérico) con detalle y «ojito» de secretos (auditado)."),
        ("Webhooks entrantes", "firmados con HMAC-SHA256 (X-Signature) para recibir eventos."),
        ("Fuentes de datos legadas", "BD de solo lectura (DSN + SELECT) y CSV → repositorio + RAG."),
        ("n8n", "puente universal gestionado; automatizaciones con acción «workflow»."),
        ("API pública /v1", "sistemas externos llaman con X-API-Key."),
    ])

    # ---- 9. Toolkit de acciones
    doc.add_heading("9. Toolkit de acciones (Google / Microsoft)", level=1)
    para("Las lecturas corren al instante; las escrituras requieren aprobación humana (o «Permitir "
         "siempre», revocable). Todo se audita.")
    table(["Acción", "Proveedor", "Escritura", "Parámetros"], [list(a) for a in ACTIONS])

    # ---- 10. Modelos y proveedores
    doc.add_heading("10. Modelos y proveedores", level=1)
    para("Rutas: local (Ollama), VPC (vLLM/TGI), open (NaN Builders), premium (OpenAI/Claude/Gemini "
         "compatible). Todas usan endpoints compatibles con OpenAI. El proveedor abierto por defecto es "
         "NaN Builders (API compatible OpenAI en https://api.nan.builders/v1).")
    doc.add_heading("Modelos publicados de NaN", level=2)
    table(["Modelo", "Tipo", "Contexto", "Capacidades"], [list(m) for m in NAN_MODELS])
    para("Nota: la API documentada de NaN no expone generación de imágenes (es una función de su web). "
         "La sección «Generar imágenes» usa la ruta estándar de OpenAI y funciona con cualquier proveedor "
         "que la exponga.", italic=True, color=GREY)

    # ---- 11. Roles y permisos
    doc.add_heading("11. Roles, permisos y multi-tenant", level=1)
    table(["Rol", "Puede"], [
        ["super_admin", "Todo, a través de todos los tenants."],
        ["admin", "Configuración del tenant: marca, facturación, usuarios, modelos, integraciones."],
        ["user", "Usar casos, agentes, documentos, automatizaciones."],
        ["security", "Auditoría, políticas y revisión de eventos."],
        ["devops", "Conectores e integraciones técnicas (fuentes de datos)."],
    ])
    para("Los permisos son jerárquicos por área y licencia: el rol y el área deciden qué documentos y "
         "contexto ve cada quien. General/sin área es visible para todos; Admin, Security y Super Admin "
         "ven todas las áreas. La autenticación es JWT (Bearer); SSO/OIDC es opcional.")

    # ---- 12. Seguridad
    doc.add_heading("12. Seguridad, privacidad y cumplimiento", level=1)
    bullets([
        ("Cifrado en reposo", "AES-256-GCM por tenant (documentos, fragmentos, credenciales)."),
        ("Redacción de PII", "antes de cualquier salida externa."),
        ("Minimización de contexto", "solo se envía lo necesario, nunca documentos completos sin autorización."),
        ("Auditoría", "cada evento registra usuario, ruta, modelo, tokens, costo, sensibilidad y razón; export a SIEM (JSONL)."),
        ("Endurecimiento", "denylist DML/CTE en fuentes de datos, escapado OData en Graph, authz de config solo super admin."),
        ("Cumplimiento de referencia", "LFPDPPP, OWASP Top 10 for LLM Apps 2025, NIST AI RMF."),
    ])

    # ---- 13. Entornos / CI-CD
    doc.add_heading("13. Entornos, CI/CD y flujo Git", level=1)
    para("Promoción dev → qa → main (producción) mediante Pull Requests con CI obligatorio "
         "(pytest de la API + build del portal). Cada push a main despliega el portal (Vercel) y la "
         "API (Render). Las migraciones son aditivas e idempotentes para no perder datos. Se recomienda "
         "proteger las ramas main y qa (requerir PR + checks en verde).")

    # ---- 14. Configuración (env vars)
    doc.add_heading("14. Configuración y despliegue", level=1)
    para("Variables de entorno principales (Backend en Render salvo la última, que es del portal):")
    table(["Variable(s)", "Grupo", "Descripción"], [[a, b, c] for a, b, c in ENVVARS])
    doc.add_heading("Checklist de puesta a punto", level=2)
    bullets([
        "SECRET_KEY, DATABASE_URL (Supabase), CORS_ORIGINS.",
        "NEXT_PUBLIC_API_BASE_URL en Vercel.",
        "NaN: OPEN_ENABLED/_API_KEY/_BASE_URL/_MODEL (+ ALLOW_CLOUD_FALLBACK si aplica).",
        "Premium: PREMIUM_* (opcional) + Probar conexión en Admin → Modelos externos.",
        "Microsoft/Google: client id/secret/redirect + reconectar para scopes de acciones.",
        "n8n: N8N_ENABLED/_WEBHOOK_BASE_URL/_API_BASE_URL/_API_KEY.",
        "Marca (white-label), plan/asientos, dominio + SSL.",
        "Proteger ramas main/qa en GitHub.",
    ])

    # ---- 15. Operación y soporte
    doc.add_heading("15. Operación y soporte", level=1)
    bullets([
        ("Ayuda in-app", "guías paso a paso en español + ayuda contextual (popup) por sección."),
        ("Salud", "el backend expone /health; Render Starter evita que el backend se «duerma»."),
        ("Primer acceso lento", "si el plan duerme por inactividad, el primer request lo despierta (~50 s)."),
        ("Contenido genérico (mock)", "indica que la ruta no tiene modelo real conectado: configúralo en Admin."),
    ])

    # ---- 16. Planes
    doc.add_heading("16. Planes y licenciamiento", level=1)
    para("Planes (MXN) por asiento con setup + anual: Emprende / Negocio / Empresa / Gobierno. "
         "El alta de usuarios respeta el número de asientos licenciados (enforcement) y el estado de la "
         "suscripción. El panel de Admin incluye un estimador de costo.")

    # ---- 17. Roadmap
    doc.add_heading("17. Roadmap y pendientes", level=1)
    bullets([
        ("Catálogos de configuración empresarial", "en definición con el cliente."),
        ("TTS/STT (NaN kokoro/whisper)", "voz y transcripción de audio hacia el RAG."),
        ("SFTP", "conector para sistemas legados (requiere paramiko)."),
        ("Pendientes del cliente", "proteger ramas, reconectar Microsoft con scopes nuevos, configurar premium/NaN."),
    ])

    # ---- Appendices
    doc.add_page_break()
    doc.add_heading("Apéndice A · Catálogo de endpoints de la API", level=1)
    para(f"La API expone {sum(len(v) for v in ENDPOINTS.values())}+ rutas (selección agrupada de 131 totales):", color=GREY)
    for group, eps in ENDPOINTS.items():
        doc.add_heading(group, level=3)
        bullets(eps)

    doc.add_heading("Apéndice B · Variables de entorno (detalle)", level=1)
    table(["Variable(s)", "Grupo", "Descripción"], [[a, b, c] for a, b, c in ENVVARS])

    doc.save(path)


# ===================================================================== PPTX
def build_pptx(path: str) -> None:
    prs = Presentation(); prs.slide_width = PInches(13.333); prs.slide_height = PInches(7.5)
    blank = prs.slide_layouts[6]

    def slide(title, bullets=None, subtitle=None, cover=False, rows=None):
        s = prs.slides.add_slide(blank)
        if cover:
            f = s.background.fill; f.solid(); f.fore_color.rgb = PV
        tb = s.shapes.add_textbox(PInches(0.7), PInches(2.6 if cover else 0.45), PInches(12), PInches(1.2))
        p = tb.text_frame.paragraphs[0]; p.word_wrap = True
        r = p.add_run(); r.text = title; r.font.size = PPt(38 if cover else 28); r.font.bold = True
        r.font.color.rgb = PW if cover else PV
        if subtitle:
            sb = s.shapes.add_textbox(PInches(0.7), PInches(3.9 if cover else 1.45), PInches(12), PInches(1))
            sp = sb.text_frame.paragraphs[0]; sp.word_wrap = True
            rr = sp.add_run(); rr.text = subtitle; rr.font.size = PPt(16); rr.font.color.rgb = PW if cover else PG
        if bullets:
            body = s.shapes.add_textbox(PInches(0.8), PInches(1.7), PInches(11.7), PInches(5.3))
            bf = body.text_frame; bf.word_wrap = True
            for i, b in enumerate(bullets):
                para = bf.paragraphs[0] if i == 0 else bf.add_paragraph()
                if isinstance(b, tuple):
                    r1 = para.add_run(); r1.text = b[0] + ": "; r1.font.bold = True; r1.font.size = PPt(15); r1.font.color.rgb = PS
                    r2 = para.add_run(); r2.text = b[1]; r2.font.size = PPt(13); r2.font.color.rgb = PG
                else:
                    r = para.add_run(); r.text = "• " + b; r.font.size = PPt(15); r.font.color.rgb = PS
                para.space_after = PPt(6)
        if rows:
            tbl = s.shapes.add_table(len(rows) + 1, len(rows[0]), PInches(0.8), PInches(1.8),
                                     PInches(11.7), PInches(0.4 * (len(rows) + 1))).table
            for j, h in enumerate(rows[0] if False else []):
                pass
        return s

    slide("MaestroAI", subtitle="Documentación técnica y funcional · 2026", cover=True)
    slide("El problema", [
        "Las empresas quieren IA pero no pueden exponer datos sensibles ni perder control.",
        "Los asistentes genéricos no clasifican, no auditan y no respetan políticas por área.",
        "Falta trazabilidad, gobierno de costo y soberanía de datos (LFPDPPP).",
    ], subtitle="Por qué MaestroAI y no «otro ChatGPT».")
    slide("La propuesta", [
        ("Capa privada y gobernada", "sobre cualquier modelo."),
        ("Enrutador de Privacidad", "clasifica, redacta y decide la ruta por cada dato."),
        ("RAG por área", "respuestas con fuentes citadas y permisos."),
        ("Integraciones", "Google/Microsoft, CRM/ERP, n8n, BD/CSV."),
    ])
    slide("Arquitectura", [
        ("Portal", "Next.js 15 + Tailwind en Vercel (PWA)."),
        ("API", "FastAPI + SQLModel en Render; Postgres (Supabase)."),
        ("RAG", "embeddings cifrados + reranking + citas."),
        ("Modelos", "local (Ollama) · VPC (vLLM) · open (NaN) · premium."),
        ("CI/CD", "dev → qa → main con pytest + build."),
    ])
    slide("Enrutador de Privacidad", [
        ("Restringido", "Local, nunca sale."),
        ("Confidencial / PII", "VPC o local."),
        ("Interno / Público", "NaN (open); premium a demanda."),
        ("Inyección/exfiltración", "Bloqueado y auditado."),
    ], subtitle="El usuario nunca elige el modelo: lo decide la política.")
    slide("NaN-primero + cascada", [
        ("Inicio", "datos no sensibles empiezan en NaN (barato/rápido)."),
        ("Escalada", "premium solo con «máxima precisión» o si la respuesta es insuficiente."),
        ("Sin premium", "todo en NaN; sin NaN, modo demostración."),
        ("Eficiencia", "condensación + tope de gasto + rerank."),
    ])
    slide("Módulos funcionales (1/2)", [(m[0], m[1]) for m in MODULES[:6]])
    slide("Módulos funcionales (2/2)", [(m[0], m[1]) for m in MODULES[6:]])
    slide("Integraciones", [
        ("Correo", "Outlook/Gmail/IMAP, multi-cuenta."),
        ("Acciones", "Gmail/Outlook, Calendar, Sheets/Excel, Teams, SharePoint."),
        ("Conectores/Webhooks", "CRM/ERP + HMAC entrante."),
        ("Legados", "BD solo lectura y CSV → RAG; n8n para el resto."),
    ])
    slide("Modelos de NaN", [
        ("qwen3.6", "principal (chat, tools, visión, reasoning)."),
        ("deepseek-v4-flash / mimo-v2.5", "1M tokens; mimo omnimodal."),
        ("qwen3-embedding / rerank", "stack RAG."),
        ("kokoro / whisper", "TTS / STT."),
    ])
    slide("Seguridad y cumplimiento", [
        "Cifrado en reposo AES-256-GCM por tenant.",
        "Redacción de PII y minimización de contexto.",
        "Auditoría total + export a SIEM.",
        "LFPDPPP · OWASP LLM 2025 · NIST AI RMF.",
    ])
    slide("Roles y gobierno", [
        ("super_admin / admin", "multi-tenant / configuración del tenant."),
        ("user / security / devops", "uso / auditoría / integraciones."),
        ("Permisos por área y licencia", "cada quien ve lo suyo."),
    ])
    slide("Entornos y operación", [
        "dev → qa → main con CI obligatorio.",
        "Despliegue: Vercel (portal) + Render (API).",
        "Ayuda in-app + contextual (popup) por sección.",
        "Auditoría navegable de cada acción.",
    ])
    slide("Roadmap", [
        ("Catálogos de configuración empresarial", "en definición."),
        ("TTS/STT (NaN)", "voz y transcripción."),
        ("SFTP", "conector legado."),
    ])
    slide("Gracias", subtitle="MaestroAI · Documentación 2026", cover=True)

    prs.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    dx = os.path.join(OUT, "MaestroAI-Documentacion.docx")
    px = os.path.join(OUT, "MaestroAI-Presentacion.pptx")
    build_docx(dx); build_pptx(px)
    print("OK", dx, px)
