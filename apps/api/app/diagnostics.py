"""Autochequeo de preparación (readiness): revisa la configuración y, por cada
hueco, devuelve una **guía de cómo resolverlo ahí mismo**.

Cada check: {key, label, status: "ok"|"warn"|"missing", detail, fix:{steps[], help, link}}.
- "ok"      → configurado / disponible.
- "warn"    → opcional o degradado (funciona, pero conviene completarlo).
- "missing" → falta algo necesario para esa capacidad.
"""
from __future__ import annotations

import shutil

from sqlmodel import select

from .config import settings


def _provider_rows(session) -> dict:
    from .models import ProviderSetting
    return {r.route: r for r in session.exec(select(ProviderSetting)).all()}


def _ok(key, label, detail):
    return {"key": key, "label": label, "status": "ok", "detail": detail, "fix": None}


def _gap(key, label, status, detail, steps, help=None, link=None):
    return {"key": key, "label": label, "status": status, "detail": detail,
            "fix": {"steps": steps, "help": help, "link": link}}


def run_checks(session, tenant, user) -> dict:
    """Devuelve {summary:{ok,warn,missing}, checks:[...]}."""
    from .integrations import token_store

    rows = _provider_rows(session)
    checks: list[dict] = []

    # 1. Modelo abierto (NaN) — base del enrutamiento.
    op = rows.get("open")
    if op and op.enabled and op.base_url:
        checks.append(_ok("model_open", "Modelo abierto (NaN)", f"Configurado: {op.model or 'modelo por defecto'}."))
    else:
        checks.append(_gap("model_open", "Modelo abierto (NaN)", "warn",
                           "Sin proveedor abierto: el chat corre en modo demostración (mock).",
                           ["Entra a *Admin → Modelos y conectores*.",
                            "En la ruta **open (NaN)** pon Base URL `https://api.nan.builders/v1`, el modelo y tu API key.",
                            "Pulsa **Probar conexión** para verificar (latencia + muestra)."],
                           help="modelos", link="/admin"))

    # 2. Modelo premium — escalada de la cascada.
    pr = rows.get("premium")
    if pr and pr.enabled and pr.base_url:
        checks.append(_ok("model_premium", "Modelo premium (escalada)", f"Configurado: {pr.model or 'modelo'}."))
    else:
        checks.append(_gap("model_premium", "Modelo premium (escalada)", "warn",
                           "Sin premium: la cascada no puede escalar a un modelo externo de mayor precisión.",
                           ["Entra a *Admin → Modelos y conectores*.",
                            "En la ruta **premium** pon Base URL, modelo y API key (OpenAI/Claude/etc.).",
                            "Pulsa **Probar conexión**."],
                           help="modelos", link="/admin"))

    # 3. On-prem (Ollama/VPC) — opcional.
    onprem = [r for k in ("local", "vpc") if (r := rows.get(k)) and r.enabled and r.base_url]
    if onprem:
        checks.append(_ok("model_onprem", "Integración on-prem", f"{len(onprem)} ruta(s) local/VPC activas."))
    else:
        checks.append(_gap("model_onprem", "Integración on-prem", "warn",
                           "Sin rutas locales: lo confidencial no puede procesarse con tu infra (Ollama/VPC).",
                           ["Levanta tu modelo local (Ollama `/v1`) y exponlo por túnel.",
                            "En *Admin → Modelos y conectores*, ruta **local**, pon la Base URL del túnel y el modelo.",
                            "Pulsa **Probar conexión**."],
                           help="onprem", link="/admin"))

    # 4. n8n — automatizaciones/workflows.
    if (settings.n8n_enabled and settings.n8n_webhook_base_url) or tenant.n8n_webhook_base_url:
        checks.append(_ok("n8n", "Automatizaciones (n8n)", "Webhook de n8n configurado."))
    else:
        checks.append(_gap("n8n", "Automatizaciones (n8n)", "warn",
                           "Sin n8n: los workflows quedan en modo simulado.",
                           ["Despliega n8n (self-hosted) y exponlo por túnel/HTTPS.",
                            "En *Integraciones* conecta tu n8n (Base URL del webhook + token), o configura `N8N_WEBHOOK_BASE_URL`.",
                            "Importa los flujos de `integrations/n8n/` si aplica."],
                           help="webhooks", link="/integrations"))

    # 4a-bis. Vector store del RAG — in-process (default) vs Qdrant/pgvector (escala).
    vs = settings.vector_store
    if vs in ("qdrant", "pgvector"):
        try:
            from .ai.vectorstore import get_vector_store
            get_vector_store()  # construye/conecta; lanza si falta dep o no alcanza
            checks.append(_ok("vector_store", "Vector store (escala)",
                              f"{vs} activo (dim {settings.embeddings_dim})."))
        except Exception as exc:
            checks.append(_gap("vector_store", "Vector store (escala)", "missing",
                               f"VECTOR_STORE={vs} pero no se pudo inicializar: {exc}",
                               ["Qdrant: provisiona el servidor + `QDRANT_URL`/`QDRANT_API_KEY` e instala `qdrant-client`.",
                                "pgvector: usa Postgres con la extensión `vector` (Supabase la trae).",
                                "Asegura `EMBEDDINGS_DIM` igual a tu modelo (qwen3-embedding = 4096).",
                                "Tras activarlo, **re-indexa** (`POST /documents/reindex`) para poblar el store."],
                               help="modelos", link="/admin"))
    else:
        checks.append(_ok("vector_store", "Vector store (escala)",
                          "In-process (vectores en la BD). Suficiente; sube a Qdrant/pgvector a gran escala."))

    # 4b. Embeddings del RAG — local (hashing) vs NaN (qwen3-embedding).
    if settings.embeddings_provider in ("open", "nan", "nanbuilders"):
        checks.append(_ok("embeddings", "Embeddings del RAG", f"Vía proveedor abierto ({settings.embeddings_model})."))
    else:
        checks.append(_gap("embeddings", "Embeddings del RAG", "warn",
                           "El RAG usa un embebedor local (hashing): recuperación de menor precisión.",
                           ["Pon `EMBEDDINGS_PROVIDER=open`, `EMBEDDINGS_MODEL=qwen3-embedding`, `EMBEDDINGS_DIM=4096`.",
                            "**Re-indexa** los documentos (botón *Re-indexar* en Documentos o `POST /documents/reindex`) para reconstruir los vectores con la nueva dimensión."],
                           help="modelos", link="/documents"))

    # 5. Toolkit de acciones — proveedor conectado Y con token legible (no solo que exista).
    from .security.crypto import decrypt, is_encrypted
    conns = token_store.list_connections(session, tenant.id, user.id)

    def _token_ok(c) -> bool:
        if not c.access_token_enc:
            return False
        return not is_encrypted(decrypt(c.access_token_enc, tenant.kms_key_id))

    usable = {c.provider for c in conns if _token_ok(c)}
    broken = {c.provider for c in conns if not _token_ok(c)}
    if usable:
        extra = f" (reconectar: {', '.join(sorted(broken))})" if broken else ""
        checks.append(_ok("actions", "Toolkit de acciones", f"Conectado: {', '.join(sorted(usable))}.{extra}"))
    elif broken:
        # El registro existe pero el token no se puede descifrar (típico tras rotar la llave KMS).
        checks.append(_gap("actions", "Toolkit de acciones", "missing",
                           f"Conexión de {', '.join(sorted(broken))} ilegible: el token quedó cifrado con una llave "
                           "anterior (rotaste MASTER_KMS_KEY/SECRET_KEY). El toolkit no funcionará hasta reconectar.",
                           ["Entra a *Integraciones*.",
                            "**Desconecta** la cuenta afectada y **vuelve a conectarla** (re-guarda el token con la llave actual).",
                            "Repite por cada proveedor marcado."],
                           help="acciones", link="/integrations"))
    else:
        checks.append(_gap("actions", "Toolkit de acciones", "warn",
                           "Sin Google/Microsoft conectado: el agente no puede ejecutar correo/calendario/Sheets.",
                           ["Entra a *Integraciones*.",
                            "Conecta **Google** y/o **Microsoft 365** (OAuth).",
                            "Otorga los scopes de escritura si quieres enviar correo/crear eventos."],
                           help="acciones", link="/integrations"))

    # 6. Antivirus en la ingesta.
    if settings.antivirus_enabled:
        checks.append(_ok("antivirus", "Antivirus en ingesta", "Activo (EICAR + ClamAV opcional)."))
    else:
        checks.append(_gap("antivirus", "Antivirus en ingesta", "warn",
                           "Antivirus desactivado: los archivos subidos no se escanean.",
                           ["Pon `ANTIVIRUS_ENABLED=true` en el backend.",
                            "Opcional: configura `CLAMAV_HOST/PORT` para escaneo completo."]))

    # 7. OCR (tesseract) para escaneados.
    if shutil.which("tesseract"):
        checks.append(_ok("ocr", "OCR de escaneados", "Tesseract disponible."))
    else:
        checks.append(_gap("ocr", "OCR de escaneados", "warn",
                           "Sin tesseract: los PDFs escaneados (sin capa de texto) no se podrán leer.",
                           ["Instala `tesseract-ocr` + `poppler-utils` en la imagen del backend (ya en el Dockerfile).",
                            "Verifica que el contenedor de Render usa esa imagen."]))

    # 8. Fine-tuning — trainer configurado.
    if settings.finetune_enabled and settings.finetune_trainer_url:
        checks.append(_ok("finetune", "Fine-tuning (trainer)", "Trainer LoRA configurado."))
    else:
        checks.append(_gap("finetune", "Fine-tuning (trainer)", "warn",
                           "Sin trainer: los jobs de LoRA quedan en modo laboratorio (simulado).",
                           ["Levanta tu laboratorio MLX y el workflow n8n (`integrations/n8n/`).",
                            "Pon `FINETUNE_ENABLED=true` y `FINETUNE_TRAINER_URL=<webhook>` en el backend.",
                            "Lanza un job desde *Fine-tuning*."],
                           help="finetune", link="/finetune"))

    # 9. MFA del usuario actual.
    if getattr(user, "mfa_enabled", False):
        checks.append(_ok("mfa", "MFA (tu cuenta)", "Verificación en dos pasos activa."))
    else:
        checks.append(_gap("mfa", "MFA (tu cuenta)", "warn",
                           "Tu cuenta no tiene verificación en dos pasos.",
                           ["Entra a *Mi cuenta*.",
                            "Activa **MFA (TOTP)** escaneando el QR con tu app autenticadora.",
                            "Guarda los **códigos de respaldo**."],
                           link="/account"))

    # 10. Cifrado en reposo — clave maestra dedicada.
    if settings.master_kms_key:
        checks.append(_ok("crypto", "Cifrado en reposo", "Clave maestra dedicada configurada."))
    else:
        checks.append(_gap("crypto", "Cifrado en reposo", "warn",
                           "Usando `SECRET_KEY` como clave de cifrado (sirve, pero conviene una dedicada).",
                           ["Define `MASTER_KMS_KEY` (32+ caracteres) en el backend.",
                            "Rota credenciales sensibles tras configurarla."]))

    # 11. Programador (scheduler) — resúmenes de correo y alertas automáticas.
    if settings.scheduler_enabled:
        checks.append(_ok("scheduler", "Automatización programada", "Scheduler activo: digests y alertas corren solos."))
    else:
        checks.append(_gap("scheduler", "Automatización programada", "warn",
                           "Scheduler apagado: los resúmenes de correo y las alertas no corren solos (solo manual).",
                           ["Pon `SCHEDULER_ENABLED=true` en el backend y reinicia.",
                            "Verifica los horarios en *Resumen de correo* y *Alertas*."],
                           help="webhooks", link="/mail-digest"))

    # 12. OAuth de correo a nivel plataforma (M365 / Google) — habilita conectar cuentas.
    oauth_on = [n for n, on in (("Microsoft 365", settings.microsoft_oauth_enabled),
                                ("Google", settings.google_oauth_enabled)) if on]
    if oauth_on:
        checks.append(_ok("oauth_config", "OAuth de correo (plataforma)", f"Habilitado: {', '.join(oauth_on)}."))
    else:
        checks.append(_gap("oauth_config", "OAuth de correo (plataforma)", "missing",
                           "Sin OAuth configurado: nadie puede conectar Outlook/Gmail (resumen de correo y acciones).",
                           ["Crea una app en Entra (Microsoft) y/o Google Cloud (OAuth).",
                            "Pon `MICROSOFT_OAUTH_ENABLED=true` + client_id/secret/redirect_uri (y/o las de Google).",
                            "Para Microsoft son scopes **delegados** (Mail.Read/Send…), distinta de la app-only de SharePoint."],
                           help="acciones", link="/integrations"))

    # 13. WhatsApp (CallMeBot) — canal de alertas del usuario actual.
    if getattr(user, "callmebot_phone", "") and getattr(user, "callmebot_apikey_enc", ""):
        checks.append(_ok("whatsapp", "WhatsApp para alertas", "CallMeBot configurado en tu cuenta."))
    else:
        checks.append(_gap("whatsapp", "WhatsApp para alertas", "warn",
                           "Sin WhatsApp: las alertas no se pueden entregar por ese canal.",
                           ["Pide tu apikey gratis a CallMeBot (callmebot.com).",
                            "En *Alertas* / *Mi cuenta* guarda tu número (+52…) y la apikey."],
                           help="alertas", link="/alerts"))

    # 14. Tablero Financiero — datos cargados (vs demo).
    try:
        from .finance import store
        row_exists = store.status(session, tenant).get("loaded")
        data = store.get_dataset(session, tenant) if row_exists else None
    except Exception:
        row_exists, data = False, None
    if data:
        checks.append(_ok("finance_data", "Tablero Financiero (datos)", "Dataset del cliente cargado."))
    elif row_exists:
        # Hay registro pero no se pudo descifrar (rotación de llave KMS).
        checks.append(_gap("finance_data", "Tablero Financiero (datos)", "missing",
                           "El dataset cargado quedó ilegible: se cifró con una llave anterior (rotaste la llave KMS). "
                           "Hay que volver a subirlo.",
                           ["Entra a *Espacio → Tablero Financiero*.",
                            "Pulsa **Cargar datos** y vuelve a subir los Excel/zip o el JSON."],
                           help="finanzas", link="/espacios"))
    else:
        checks.append(_gap("finance_data", "Tablero Financiero (datos)", "warn",
                           "El tablero muestra datos demo: aún no se cargan los del cliente.",
                           ["Entra a un *Espacio → Tablero Financiero*.",
                            "Pulsa **Cargar datos** y sube los Excel/zip o el dataset JSON.",
                            "Más adelante, automatízalo con el conector de SharePoint/BD (Paso 1)."],
                           help="finanzas", link="/espacios"))

    summary = {"ok": 0, "warn": 0, "missing": 0}
    for c in checks:
        summary[c["status"]] = summary.get(c["status"], 0) + 1
    return {"summary": summary, "checks": checks}
