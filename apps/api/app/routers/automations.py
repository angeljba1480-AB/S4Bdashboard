"""/automations — create automations from templates, enable/disable, run now.

Action dispatch: workflow (n8n), recipe (use-case engine), or notify (audit).
Schedules/events are executed by the workflows layer (n8n/Temporal); this module
manages definitions and immediate runs.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..automations.catalog import TEMPLATES, get_template
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations.n8n import resolve_n8n, trigger_workflow
from ..models import Automation, AuditEvent, Notification, Tenant, User

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationIn(BaseModel):
    name: str
    description: str = ""
    trigger: str = "manual"
    schedule: str = ""
    event: str = ""
    action_type: str = "workflow"
    action_ref: str = ""
    config: dict = {}


class FromTemplate(BaseModel):
    template_id: str


def _out(a: Automation) -> dict:
    return {"id": a.id, "name": a.name, "description": a.description, "trigger": a.trigger,
            "schedule": a.schedule, "event": a.event, "action_type": a.action_type,
            "action_ref": a.action_ref, "config": json.loads(a.config or "{}"),
            "enabled": a.enabled, "status": a.status, "last_run": a.last_run or None}


def _load(session, tenant, user, aid) -> Automation:
    a = session.get(Automation, aid)
    if not a or a.tenant_id != tenant.id or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    return a


_CHANNELS = ("notify", "whatsapp", "email")

# Fuentes de entrada para una automatización (qué va a procesar antes de correr).
_SOURCE_KINDS = ("new_documents", "drive_folder", "datasource", "manual")
_SOURCE_LABELS = {
    "new_documents": "Documentos nuevos",
    "drive_folder": "Carpeta de Drive",
    "datasource": "Fuente de datos (legado)",
    "manual": "Sin entrada (manual)",
}


def _deliver_result(session: Session, tenant: Tenant, owner_id: str | None,
                    name: str, content: str, config: dict) -> str:
    """Entrega el resultado de una automatización a los canales elegidos
    (notificación / WhatsApp / correo). Devuelve los canales a los que se envió."""
    content = (content or "").strip()
    if not content:
        return ""
    channels = [c for c in (config.get("deliver") or ["notify"]) if c in _CHANNELS]
    owner = session.get(User, owner_id) if owner_id else None
    sent: list[str] = []

    if "notify" in channels and owner_id:
        session.add(Notification(tenant_id=tenant.id, user_id=owner_id, title=name,
                                 body=content[:8000], event_type="automation"))
        sent.append("notificación")

    if "whatsapp" in channels and owner and owner.callmebot_phone and owner.callmebot_apikey_enc:
        try:
            from ..integrations import whatsapp
            from ..security.crypto import decrypt
            ok, _ = whatsapp.send_callmebot(
                owner.callmebot_phone, decrypt(owner.callmebot_apikey_enc, tenant.kms_key_id),
                f"{name}\n\n{content}"[:900])
            sent.append("whatsapp" if ok else "whatsapp✗")
        except Exception:
            sent.append("whatsapp✗")

    if "email" in channels:
        try:
            from ..integrations import actions_exec, token_store
            sup = token_store.support_sender(session, tenant)
            if sup:
                row, tok = sup
            else:
                conns = [c for c in token_store.list_tenant_connections(session, tenant.id)
                         if c.provider in ("microsoft", "google")]
                row = conns[0] if conns else None
                tok = token_store.access_token_for(session, tenant, row) if row else None
            to = (config.get("email_to") or (owner.email if owner else "") or (row.identifier if row else "")).strip()
            if row and tok and to:
                action = "outlook.send" if row.provider == "microsoft" else "gmail.send"
                actions_exec.execute(action, tok, {"to": to, "subject": name, "body": content[:6000]})
                sent.append(f"correo→{to}")
        except Exception:
            sent.append("correo✗")
    return ", ".join(sent)


def _run_ingesta(session: Session, tenant: Tenant, owner_id: str | None,
                 source: dict) -> tuple[str, str]:
    """Ingesta NATIVA: el indexado al RAG vive en MaestroAI, así que la
    automatización 'ingesta' lo corre aquí mismo (sin viaje a n8n).
    Indexa los documentos pendientes (`indexed=False`) según la fuente:
    - new_documents: los no indexados (opcionalmente creados desde `since`).
    - datasource: primero jala filas frescas de la fuente (que se indexan al
      importarse) y luego barre lo pendiente.
    - drive_folder/manual: barre lo pendiente (los archivos de Drive se indexan
      al importarse desde Documentos)."""
    from ..ai.rag import index_document
    from ..models import Document

    kind = (source or {}).get("kind") or "new_documents"
    extra = ""

    if kind == "datasource" and (source or {}).get("ref"):
        # Reaprovecha el import de fuentes de datos (consulta SELECT → documento + RAG).
        try:
            from ..security.crypto import decrypt
            from .datasources import _as_text, _import_as_document, _owned, _run_query
            d = _owned(session, tenant, source["ref"])
            owner = session.get(User, owner_id) if owner_id else None
            cols, rows = _run_query(decrypt(d.dsn_enc, tenant.kms_key_id), d.query)
            _import_as_document(session, tenant, owner, name=d.name,
                                content=_as_text(cols, rows), area=d.area or "",
                                category=d.category or "", storage_uri=f"datasource://{d.id}",
                                rows=len(rows), source_label=f"fuente de datos '{d.name}'")
            extra = f" · fuente '{d.name}': {len(rows)} filas"
        except Exception as exc:
            extra = f" · fuente no disponible: {exc}"

    q = select(Document).where(Document.tenant_id == tenant.id, Document.indexed == False)  # noqa: E712
    if kind == "new_documents" and (source or {}).get("since"):
        try:
            q = q.where(Document.created_at >= datetime.fromisoformat(source["since"]))
        except Exception:
            pass
    docs = session.exec(q).all()

    n_docs = n_chunks = 0
    for doc in docs:
        try:
            n_chunks += index_document(session, doc)
            n_docs += 1
        except Exception:
            continue
    if n_docs == 0 and not extra:
        return "completed", "ingesta · no hay documentos nuevos por indexar"
    return "completed", f"ingesta · {n_docs} documentos indexados ({n_chunks} fragmentos){extra}"


def _run_mando(session: Session, tenant: Tenant) -> str:
    """Centro de mando: arma un reporte ejecutivo con KPIs REALES de la operación
    (casos, tokens, costo, apps) + insights de IA. MaestroAI lo calcula y lo pasa
    a n8n para que el canvas lo enrute (correo/Slack/CRM); también se entrega."""
    from ..ai.resilience import generate_with_fallback
    from ..ai.router import route_request
    from .usage import compute_operations

    ops = compute_operations(session, tenant)
    casos, tok, cost, apps = ops["cases"], ops["tokens"], ops["cost"], ops["apps"]
    top = ", ".join(f"{k} ({v})" for k, v in list(casos["by_recipe"].items())[:5]) or "sin casos"
    ctx = (
        f"Casos: {casos['total']} (completados {casos['completed']}, en curso {casos['in_progress']}).\n"
        f"Casos por tipo: {top}.\n"
        f"Búsquedas/respuestas IA: {ops['searches']}.\n"
        f"Tokens: {tok['total']} (chat {tok['by_source']['chat']}, casos {tok['by_source']['casos']}, "
        f"apps {tok['by_source']['apps']}).\n"
        f"Costo IA acumulado: ${cost['total']}.\n"
        f"Apps: {apps['built']} construidas, {apps['deployed']} desplegadas."
    )
    system = ("Eres el centro de mando operativo de la empresa. Con los KPIs provistos, redacta en "
              "español un reporte ejecutivo BREVE con: 1) Resumen del día, 2) KPIs clave, 3) Alertas "
              "o riesgos si los datos los sugieren, 4) Recomendaciones accionables. Usa SOLO los datos "
              "provistos; no inventes cifras.")
    prompt = f"KPIs de operación:\n{ctx}\n\nGenera el reporte del centro de mando."
    try:
        decision = route_request(tenant, None, prompt, [ctx], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, decision.context or [ctx])
        report = (gen.response.content or "").strip()
    except Exception as exc:  # si no hay proveedor, entrega al menos los KPIs
        report = f"Reporte de operación (KPIs):\n{ctx}\n\n(No se pudo generar el análisis IA: {exc})"
    return report or f"Reporte de operación (KPIs):\n{ctx}"


def _run(session: Session, tenant: Tenant, user: User | None, a: Automation,
         payload: dict | None = None) -> tuple[str, str]:
    """Execute the action. Returns (status, detail)."""
    config = json.loads(a.config or "{}")
    if payload:
        config = {**config, **payload}
    # Usuario efectivo: quien ejecuta, o el dueño de la automatización (corridas
    # programadas/por evento no traen usuario, pero la cuenta conectada es del dueño).
    uid = (user.id if user else None) or a.user_id
    if a.action_type == "workflow" and a.action_ref == "ingesta":
        # El indexado al RAG vive en MaestroAI → ingesta nativa (sin viaje a n8n).
        status, detail = _run_ingesta(session, tenant, uid, dict(config.get("source") or {}))
        delivered = _deliver_result(session, tenant, uid, a.name, detail, config)
        return status, f"{detail}{f' → enviado a {delivered}' if delivered else ''}"
    if a.action_type == "workflow":
        cfg = resolve_n8n(tenant)
        # Resuelve la fuente (qué procesar) y la manda como entrada al webhook.
        # Para "documentos nuevos" añade el corte temporal (desde la última corrida).
        src = dict(config.get("source") or {})
        if src.get("kind") == "new_documents":
            src["since"] = a.last_run or ""
        payload_out = {"automation_id": a.id, "tenant_id": tenant.id, "user_id": uid,
                       "source": src, **config}
        # Centro de mando: MaestroAI calcula el reporte real y lo pasa a n8n (el
        # canvas puede enrutarlo); si n8n no lo devuelve, se entrega este mismo.
        mando_report = ""
        if a.action_ref == "mando":
            mando_report = _run_mando(session, tenant)
            payload_out["text"] = mando_report
        run = trigger_workflow(cfg, a.action_ref, payload_out)
        resp = run.response or {}
        content = ""
        if isinstance(resp, dict) and resp:
            content = str(resp.get("text") or resp.get("summary") or resp.get("result")
                          or resp.get("output") or json.dumps(resp, ensure_ascii=False))
        elif resp:
            content = str(resp)
        if not content and mando_report:
            content = mando_report
        delivered = _deliver_result(session, tenant, uid, a.name, content, config)
        extra = f" → enviado a {delivered}" if delivered else ""
        return run.status, f"workflow {a.action_ref} · n8n:{run.source} · {run.detail}{extra}"
    if a.action_type == "recipe":
        from ..recipes.catalog import execute, prefill
        from .recipes import _resolve
        recipe = _resolve(session, tenant.id, a.action_ref)
        if not recipe:
            return "failed", f"receta {a.action_ref} no encontrada"
        # Una automatización corre el caso END-TO-END (sin paso de aprobación humana):
        # prefill arma el plan, execute lo genera con datos reales.
        draft = prefill(recipe, session, tenant, config, user_id=uid)
        result = execute(recipe, session, tenant.id, config, draft, user_id=uid)
        detail = str(result.get("message") or result.get("output") or draft.get("summary", ""))
        # Entrega el resultado completo a los canales elegidos (notif/WhatsApp/correo);
        # si no, el texto se perdería: la automatización corre sola.
        doc = result.get("documento") or (result.get("output") if isinstance(result.get("output"), str) else "")
        delivered = _deliver_result(session, tenant, uid, recipe["name"], doc, config)
        if delivered:
            detail = f"{detail} → enviado a {delivered}"
        return "completed", f"caso {recipe['name']}: {detail[:200]}"
    if a.action_type == "connector":
        from .integrations import send_to_connector
        return send_to_connector(session, tenant, a.action_ref, {
            "automation": a.name, "tenant_id": tenant.id, **config})
    # notify
    return "completed", config.get("message", "Notificación enviada")


def dispatch_event(session: Session, tenant: Tenant, event: str,
                   payload: dict | None = None, user: User | None = None) -> int:
    """Run all enabled automations subscribed to an event. Returns how many ran."""
    autos = session.exec(
        select(Automation).where(
            Automation.tenant_id == tenant.id, Automation.event == event, Automation.enabled == True)  # noqa: E712
    ).all()
    ran = 0
    for a in autos:
        try:
            status, detail = _run(session, tenant, user, a, payload)
        except Exception as exc:  # never break the triggering action
            status, detail = "failed", f"error: {exc}"
        a.status = status
        a.last_run = datetime.utcnow().isoformat()
        session.add(a)
        session.add(AuditEvent(
            tenant_id=tenant.id, user_id=user.id if user else None, event_type="automation",
            object_type="automation", object_id=a.id,
            risk_level="med" if status == "failed" else "low",
            reason=f"evento '{event}' → '{a.name}' · {status} · {detail}"))
        ran += 1
    if ran:
        session.commit()
    return ran


def run_due(session: Session, tenant: Tenant, frequency: str) -> int:
    """Run enabled scheduled automations of a given frequency (daily/weekly/...)."""
    autos = session.exec(
        select(Automation).where(
            Automation.tenant_id == tenant.id, Automation.trigger == "schedule",
            Automation.schedule == frequency, Automation.enabled == True)  # noqa: E712
    ).all()
    ran = 0
    for a in autos:
        try:
            status, detail = _run(session, tenant, None, a)
        except Exception as exc:
            status, detail = "failed", f"error: {exc}"
        a.status, a.last_run = status, datetime.utcnow().isoformat()
        session.add(a)
        session.add(AuditEvent(
            tenant_id=tenant.id, event_type="automation", object_type="automation", object_id=a.id,
            risk_level="med" if status == "failed" else "low",
            reason=f"programada ({frequency}) '{a.name}' · {status} · {detail}"))
        ran += 1
    if ran:
        session.commit()
    return ran


@router.get("/templates")
def templates(_: User = Depends(get_current_user)) -> list[dict]:
    return TEMPLATES


@router.post("/run-due")
def run_due_endpoint(
    frequency: str = "daily",
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Run this tenant's due scheduled automations. Called by the scheduler or
    an external cron (works on serverless without an in-process scheduler)."""
    return {"frequency": frequency, "ran": run_due(session, tenant, frequency)}


@router.get("")
def list_automations(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(Automation).where(Automation.tenant_id == tenant.id, Automation.user_id == user.id)
        .order_by(Automation.created_at.desc())
    ).all()
    return [_out(a) for a in rows]


@router.post("", status_code=201)
def create_automation(
    body: AutomationIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    a = Automation(
        tenant_id=tenant.id, user_id=user.id, name=body.name.strip(),
        description=body.description.strip(), trigger=body.trigger, schedule=body.schedule,
        event=body.event, action_type=body.action_type, action_ref=body.action_ref.strip(),
        config=json.dumps(body.config),
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.post("/from-template", status_code=201)
def create_from_template(
    body: FromTemplate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    t = get_template(body.template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    a = Automation(
        tenant_id=tenant.id, user_id=user.id, name=t["name"], description=t["description"],
        trigger=t["trigger"], schedule=t["schedule"], event=t["event"],
        action_type=t["action_type"], action_ref=t["action_ref"], config=json.dumps(t["config"]),
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.post("/{automation_id}/toggle")
def toggle(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    a.enabled = not a.enabled
    session.add(a)
    session.commit()
    return {"id": a.id, "enabled": a.enabled}


@router.post("/{automation_id}/run")
def run_now(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    status, detail = _run(session, tenant, user, a)
    a.status = status
    a.last_run = datetime.utcnow().isoformat()
    session.add(a)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="automation",
        object_type="automation", object_id=a.id,
        risk_level="med" if status == "failed" else "low",
        reason=f"automatización '{a.name}' ejecutada · {status} · {detail}",
    ))
    session.commit()
    return {"id": a.id, "status": status, "detail": detail, "last_run": a.last_run}


@router.get("/{automation_id}/validate")
def validate(automation_id: str, tenant: Tenant = Depends(get_current_tenant),
             user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Validación previa (tipo workflow): pasos con semáforo de si está todo listo
    para ejecutar — disparador, fuente, destino y modelo."""
    a = _load(session, tenant, user, automation_id)
    config = json.loads(a.config or "{}")
    steps: list[dict] = []

    def step(label: str, ok: bool, detail: str, link: str | None = None, optional: bool = False) -> None:
        steps.append({"label": label, "status": "ok" if ok else "missing",
                      "detail": detail, "link": link, "optional": optional})

    # 1. Disparador
    if a.trigger == "manual":
        step("Disparador", True, "Manual (lo ejecutas tú)")
    elif a.trigger == "schedule":
        step("Disparador", bool(a.schedule), f"Programado · {a.schedule or 'sin frecuencia'}")
    else:
        step("Disparador", bool(a.event), f"Por evento · {a.event or 'sin evento'}")

    # 2. Fuente según la acción
    if a.action_type == "recipe":
        from ..integrations import token_store
        from .recipes import _resolve
        recipe = _resolve(session, tenant.id, a.action_ref)
        if not recipe:
            step("Caso", False, f"Caso '{a.action_ref}' no encontrado", "/recipes")
        elif recipe.get("handler") == "correo_agenda":
            conns = [c for c in token_store.list_tenant_connections(session, tenant.id)
                     if c.provider in ("microsoft", "google", "imap")]
            step("Correo conectado", bool(conns),
                 conns[0].identifier if conns else "Conecta tu correo en Integraciones", "/integrations")
        else:
            step("Caso listo", True, recipe["name"])
    elif a.action_type == "workflow" and a.action_ref == "ingesta":
        # Ingesta nativa: el indexado al RAG corre dentro de MaestroAI (sin n8n).
        from ..models import Document
        pending = session.exec(
            select(Document).where(Document.tenant_id == tenant.id, Document.indexed == False)  # noqa: E712
        ).all()
        step("Indexado (nativo)", True,
             f"Ingesta en MaestroAI · {len(pending)} documento(s) pendiente(s) de indexar")
    elif a.action_type == "workflow":
        cfg = resolve_n8n(tenant)
        step("n8n configurado", cfg.enabled,
             "Conectado" if cfg.enabled else "n8n no configurado → ejecución simulada", "/integrations")
    elif a.action_type == "connector":
        from ..models import DataSource
        ds = session.exec(select(DataSource).where(DataSource.tenant_id == tenant.id)).first()
        step("Conector (legado)", bool(ds), ds.name if ds else "Configura un datasource", "/integrations")
    else:  # notify
        step("Destino", True, "Notificación interna")

    # 2b. Entrada: qué va a procesar el flujo (común a todos los workflows).
    if a.action_type == "workflow":
        src = config.get("source") or {}
        kind = src.get("kind")
        if kind and kind in _SOURCE_KINDS:
            desc = _SOURCE_LABELS.get(kind, kind)
            ref = src.get("label") or src.get("ref")
            step("Entrada", True, f"{desc}{f': {ref}' if ref else ''}")
        else:
            step("Entrada", False,
                 "Elige qué va a procesar (carpeta, fuente de datos o documentos nuevos)",
                 optional=True)

    # 3. Modelo disponible (para casos que generan con IA)
    from ..ai.adapters import _RUNTIME
    from ..config import settings
    open_ok = bool((_RUNTIME.get("open") or {}).get("base_url")) or bool(settings.open_enabled and settings.open_base_url)
    step("Modelo (NaN)", open_ok, "Proveedor abierto activo" if open_ok else "Configura NaN en Admin → Modelos", "/admin")

    # 4. Salida: a dónde va el resultado (entrega real de la automatización).
    deliver = [c for c in (config.get("deliver") or ["notify"]) if c in _CHANNELS]
    labels = {"notify": "notificación", "whatsapp": "WhatsApp", "email": "correo"}
    step("Salida", bool(deliver), ", ".join(labels.get(c, c) for c in deliver) if deliver
         else "Define a dónde mandar el resultado (notificación, WhatsApp o correo)", optional=True)

    ready = all(s["status"] == "ok" or s.get("optional") for s in steps)
    return {"name": a.name, "ready": ready, "steps": steps}


class ScheduleIn(BaseModel):
    frequency: str = "daily"   # daily | weekly | monthly


@router.post("/{automation_id}/schedule")
def schedule(automation_id: str, body: ScheduleIn, tenant: Tenant = Depends(get_current_tenant),
             user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Programa la automatización (la deja activa con la frecuencia indicada)."""
    a = _load(session, tenant, user, automation_id)
    a.trigger = "schedule"
    a.schedule = body.frequency.strip() or "daily"
    a.enabled = True
    session.add(a)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="automation", object_type="automation",
        object_id=a.id, risk_level="low", reason=f"programada '{a.name}' · {a.schedule}"))
    session.commit()
    session.refresh(a)
    return _out(a)


class DeliveryIn(BaseModel):
    channels: list[str] = ["notify"]   # notify | whatsapp | email
    email_to: str = ""


@router.post("/{automation_id}/delivery")
def set_delivery(automation_id: str, body: DeliveryIn, tenant: Tenant = Depends(get_current_tenant),
                 user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Define a dónde va el resultado de la automatización (notificación/WhatsApp/correo)."""
    a = _load(session, tenant, user, automation_id)
    cfg = json.loads(a.config or "{}")
    cfg["deliver"] = [c for c in body.channels if c in _CHANNELS] or ["notify"]
    if body.email_to.strip():
        cfg["email_to"] = body.email_to.strip()
    a.config = json.dumps(cfg)
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


class SourceIn(BaseModel):
    kind: str = "new_documents"   # new_documents | drive_folder | datasource | manual
    ref: str = ""                 # id de carpeta/datasource según el tipo
    label: str = ""               # nombre legible para mostrar


@router.post("/{automation_id}/source")
def set_source(automation_id: str, body: SourceIn, tenant: Tenant = Depends(get_current_tenant),
               user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Define qué va a procesar la automatización antes de ejecutar (la entrada).
    Se manda como `source` en el payload del workflow/n8n."""
    kind = body.kind if body.kind in _SOURCE_KINDS else "new_documents"
    a = _load(session, tenant, user, automation_id)
    cfg = json.loads(a.config or "{}")
    cfg["source"] = {"kind": kind, "ref": body.ref.strip(), "label": body.label.strip()}
    a.config = json.dumps(cfg)
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.delete("/{automation_id}")
def delete_automation(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    session.delete(a)
    session.commit()
    return {"ok": True}
