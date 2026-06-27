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

    # 4b. Embeddings del RAG — local (hashing) vs NaN (qwen3-embedding).
    if settings.embeddings_provider in ("open", "nan", "nanbuilders"):
        checks.append(_ok("embeddings", "Embeddings del RAG", f"Vía proveedor abierto ({settings.embeddings_model})."))
    else:
        checks.append(_gap("embeddings", "Embeddings del RAG", "warn",
                           "El RAG usa un embebedor local (hashing): recuperación de menor precisión.",
                           ["Pon `EMBEDDINGS_PROVIDER=open`, `EMBEDDINGS_MODEL=qwen3-embedding`, `EMBEDDINGS_DIM=4096`.",
                            "**Re-indexa** los documentos (botón *Re-indexar* en Documentos o `POST /documents/reindex`) para reconstruir los vectores con la nueva dimensión."],
                           help="modelos", link="/documents"))

    # 5. Toolkit de acciones — proveedor conectado (Google/Microsoft).
    connected = {c.provider for c in token_store.list_connections(session, tenant.id, user.id)}
    if connected:
        checks.append(_ok("actions", "Toolkit de acciones", f"Conectado: {', '.join(sorted(connected))}."))
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

    summary = {"ok": 0, "warn": 0, "missing": 0}
    for c in checks:
        summary[c["status"]] = summary.get(c["status"], 0) + 1
    return {"summary": summary, "checks": checks}
