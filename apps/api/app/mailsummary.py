"""Resumen de correo automatizado (genérico y configurable).

Toma el patrón del handoff Apps Script y lo lleva a la plataforma: clasifica el buzón
conectado (categoría + prioridad), descarta propaganda, detecta pendientes por responder,
aprende un perfil de remitentes y entrega por pop-up / correo / WhatsApp. Cron-friendly
(lo dispara un cron externo vía /mail-digest/run), sin servidor propio.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlmodel import select

from .models import MailDigestConfig, Notification, Tenant, User

CATEGORIES = ["Escuela", "Finanzas", "Salud", "Trabajo", "Personal", "Hogar/Servicios", "Otro"]
_PRIO_ORDER = {"alta": 0, "media": 1, "baja": 2}
_PRIO_EMOJI = {"alta": "🔴", "media": "🟡", "baja": "🔵"}


def _load(raw: str, default):
    try:
        v = json.loads(raw or "")
        return v if isinstance(v, type(default)) else default
    except (ValueError, TypeError):
        return default


def _profile_text(profile: dict) -> str:
    if not profile:
        return ""
    return "\n".join(f"{e} -> {'PROPAGANDA' if v.get('propaganda') else v.get('categoria', 'Otro')}"
                     for e, v in list(profile.items())[:150])


def _build_prompt(messages: list[dict], cfg: MailDigestConfig, profile: dict) -> str:
    lista = "\n\n".join(
        f"--- Correo {i+1} ---\nDe: {m.get('from','')}\nAsunto: {m.get('subject','')}\n"
        f"{'NO LEÍDO' if m.get('unread') else 'leído'}\nVista: {m.get('preview','')}"
        for i, m in enumerate(messages))
    bloque_notas = f"\nContexto de la organización (tenlo en cuenta): {cfg.notes}\n" if cfg.notes.strip() else ""
    ctx = _profile_text(profile)
    bloque_ctx = (f"\nCONTEXTO — remitentes ya conocidos (guía, pero el contenido de hoy manda):\n{ctx}\n"
                  if ctx else "")
    biling = ("BILINGÜE: en 'asunto_breve', 'resumen' y 'accion' escribe primero español, luego '\\n' "
              "(literal) y luego inglés.\n" if cfg.language == "bilingue" else "")
    descarta = ("Descarta la propaganda/publicidad/newsletters/spam: NO la incluyas en items, solo cuéntala "
                "en num_descartados.\n" if cfg.discard_propaganda else "")
    pend = ("Marca en 'pendiente' los correos que parecen esperar TU respuesta (preguntas, solicitudes) "
            "de remitentes no automáticos.\n" if cfg.pending_enabled else "")
    return (
        "Eres un asistente que revisa el correo del día. Te paso los correos recibidos.\n"
        f"{bloque_notas}{bloque_ctx}\n"
        f"Para cada correo asigna CATEGORÍA ({', '.join(CATEGORIES)}) y PRIORIDAD (alta|media|baja).\n"
        f"{descarta}{pend}{biling}"
        "Devuelve SOLO un JSON válido (sin markdown) con la forma:\n"
        '{"items":[{"categoria":"","prioridad":"alta","remitente":"","asunto_breve":"",'
        '"resumen":"","accion":"","fecha_limite":"","pendiente":false}],"num_descartados":0}\n\n'
        f"Correos del día:\n{lista}")


def _parse(text: str) -> dict:
    t = (text or "").replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(t)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data
    except (ValueError, TypeError):
        pass
    return {"items": [{"categoria": "Otro", "prioridad": "media", "remitente": "",
                       "asunto_breve": "Resumen del día", "resumen": t[:500], "accion": "",
                       "fecha_limite": "", "pendiente": False}], "num_descartados": 0}


def _classify(tenant: Tenant, prompt: str) -> dict:
    """Llama al modelo (router de privacidad + fallback) y parsea el JSON."""
    from .ai.resilience import generate_with_fallback
    from .ai.router import route_request
    system = ("Clasifica y resume correo. Responde SOLO JSON válido, sin texto extra. "
              "No inventes; usa solo lo provisto.")
    decision = route_request(tenant, None, prompt, [], task="recipe")
    gen = generate_with_fallback(decision.route, system, prompt, decision.context or [])
    return _parse(gen.response.content)


def _update_profile(profile: dict, items: list[dict]) -> dict:
    """Aprendizaje incremental: registra categoría por remitente visto hoy."""
    import re
    for it in items:
        raw = (it.get("remitente") or "").lower()
        m = re.search(r"<(.+?)>", raw)
        email = (m.group(1) if m else raw).strip()
        if "@" in email:
            profile[email] = {"categoria": it.get("categoria", "Otro"), "propaganda": False}
    return profile


def _render(items: list[dict], num_desc: int, cfg: MailDigestConfig) -> tuple[str, list[dict]]:
    items = sorted(items, key=lambda x: _PRIO_ORDER.get(x.get("prioridad", "baja"), 9))
    pend = [it for it in items if it.get("pendiente")] if cfg.pending_enabled else []
    lines = ["Resumen de correo de hoy:"]
    for it in items:
        em = _PRIO_EMOJI.get(it.get("prioridad", "baja"), "•")
        lines.append(f"{em} [{it.get('categoria','')}] {it.get('asunto_breve','')}")
        if it.get("resumen"):
            lines.append(f"   {it['resumen']}")
        extra = []
        if it.get("accion"):
            extra.append(f"✅ {it['accion']}")
        if it.get("fecha_limite"):
            extra.append(f"⏰ {it['fecha_limite']}")
        if extra:
            lines.append("   " + "  ·  ".join(extra))
    if pend:
        lines.append("")
        lines.append("⏳ Pendientes por responder:")
        for it in pend:
            lines.append(f"• {it.get('remitente','')} — {it.get('asunto_breve','')}")
    if num_desc:
        lines.append("")
        lines.append(f"(Descartados como propaganda/spam: {num_desc})")
    if not items and not pend:
        lines = ["Sin correos relevantes ni pendientes hoy. ✅"]
    return "\n".join(lines), pend


def build_summary(session, tenant: Tenant, user: User, cfg: MailDigestConfig) -> dict:
    """Trae el buzón, clasifica, aprende remitentes y arma el texto. No entrega."""
    from .integrations import mailbox, token_store
    conn = token_store.resolve_connection(session, tenant.id, user.id, cfg.account_id)
    if not conn:
        return {"ok": False, "reason": "no_account", "text": "",
                "message": "No hay una cuenta de correo conectada. Conéctala en Integraciones."}
    access = token_store.access_token_for(session, tenant, conn)
    if not access:
        return {"ok": False, "reason": "expired", "text": "",
                "message": "La conexión de correo expiró. Reconéctala en Integraciones."}
    data = mailbox.fetch(conn.provider, access)
    messages = data.get("messages", [])
    if not messages:
        return {"ok": True, "text": "Sin correos nuevos hoy. ✅", "items": [], "pending": [],
                "counts": {"messages": 0}, "account": conn.identifier or conn.provider, "empty": True}
    profile = _load(cfg.sender_profile, {})
    parsed = _classify(tenant, _build_prompt(messages, cfg, profile))
    items = parsed.get("items", []) or []
    text, pending = _render(items, int(parsed.get("num_descartados", 0) or 0), cfg)
    cfg.sender_profile = json.dumps(_update_profile(profile, items))[:60000]
    return {"ok": True, "text": text, "items": items, "pending": pending,
            "counts": {"messages": len(messages)}, "account": conn.identifier or conn.provider}


def deliver(session, tenant: Tenant, user: User, cfg: MailDigestConfig, summary: dict) -> dict:
    """Entrega el resumen por los canales configurados. Nunca lanza por canal."""
    channels = _load(cfg.channels, [])
    text = summary.get("text", "")
    title = "Resumen de correo de hoy"
    sent = {}
    if "popup" in channels:
        try:
            session.add(Notification(tenant_id=tenant.id, user_id=user.id, title=title,
                                     body=text[:2000], level="info", event_type="mail_digest"))
            session.commit()
            sent["popup"] = True
        except Exception:
            session.rollback()
    if "whatsapp" in channels:
        try:
            from .integrations import whatsapp as _wa
            from .security.crypto import decrypt
            if user.callmebot_phone and user.callmebot_apikey_enc:
                key = decrypt(user.callmebot_apikey_enc, tenant.kms_key_id)
                ok, _ = _wa.send_callmebot(user.callmebot_phone, key, f"{title}\n{text}")
                sent["whatsapp"] = ok
        except Exception:
            sent["whatsapp"] = False
    if "email" in channels:
        sent["email"] = _send_email(session, tenant, user, cfg, title, text)
    return sent


def _send_email(session, tenant, user, cfg, subject, text) -> bool:
    """Envía el resumen por correo usando la cuenta conectada (Gmail/Graph)."""
    try:
        from .integrations import token_store
        conn = token_store.resolve_connection(session, tenant.id, user.id, cfg.account_id)
        if not conn or conn.provider not in ("microsoft", "google"):
            return False
        access = token_store.access_token_for(session, tenant, conn)
        if not access:
            return False
        to = cfg.email_to.strip() or conn.identifier or user.email
        from .integrations import actions_exec
        action = "outlook.send" if conn.provider == "microsoft" else "gmail.send"
        actions_exec.execute(action, access, {"to": to, "subject": subject, "body": text})
        return True
    except Exception:
        return False


def run_due(session, frequency: str = "daily") -> int:
    """Ejecuta los resúmenes habilitados (cron). 'weekdays' lo decide el cron externo
    al llamar solo en días hábiles; aquí se procesan todas las configs habilitadas. Nunca lanza."""
    try:
        cfgs = session.exec(select(MailDigestConfig).where(MailDigestConfig.enabled == True)).all()  # noqa: E712
    except Exception:
        return 0
    done = 0
    for cfg in cfgs:
        try:
            tenant = session.get(Tenant, cfg.tenant_id)
            user = session.get(User, cfg.user_id)
            if not tenant or not user:
                continue
            summary = build_summary(session, tenant, user, cfg)
            if summary.get("ok"):
                deliver(session, tenant, user, cfg, summary)
            cfg.last_run_at = datetime.utcnow().isoformat()
            session.add(cfg)
            session.commit()
            done += 1
        except Exception:
            session.rollback()
    return done
