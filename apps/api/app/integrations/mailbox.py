"""Fetch a user's recent mail + today's calendar and summarize it.

Microsoft Graph and Google (Gmail/Calendar). The fetched content is sensitive,
so the summary is produced through the privacy router (PII redaction + model
routing) like everything else on the platform.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
GCAL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- Microsoft Graph --------------------------------------------------------
def _ms_messages(token: str, limit: int = 10) -> list[dict]:
    url = (f"{GRAPH}/me/messages?$top={limit}"
           "&$select=subject,from,receivedDateTime,bodyPreview,isRead"
           "&$orderby=receivedDateTime desc")
    r = httpx.get(url, headers=_auth(token), timeout=20)
    r.raise_for_status()
    out = []
    for m in r.json().get("value", []):
        frm = (m.get("from", {}) or {}).get("emailAddress", {}) or {}
        out.append({
            "from": frm.get("name") or frm.get("address", ""),
            "subject": m.get("subject", "(sin asunto)"),
            "received": m.get("receivedDateTime", ""),
            "preview": (m.get("bodyPreview", "") or "")[:240],
            "unread": not m.get("isRead", True),
        })
    return out


def _ms_events(token: str, limit: int = 15) -> list[dict]:
    now = datetime.utcnow()
    end = now + timedelta(days=1)
    url = (f"{GRAPH}/me/calendarview?startDateTime={now.isoformat()}Z"
           f"&endDateTime={end.isoformat()}Z&$select=subject,start,end,location"
           f"&$orderby=start/dateTime&$top={limit}")
    r = httpx.get(url, headers={**_auth(token), "Prefer": 'outlook.timezone="UTC"'}, timeout=20)
    r.raise_for_status()
    out = []
    for e in r.json().get("value", []):
        out.append({
            "subject": e.get("subject", "(sin título)"),
            "start": (e.get("start", {}) or {}).get("dateTime", ""),
            "end": (e.get("end", {}) or {}).get("dateTime", ""),
            "location": (e.get("location", {}) or {}).get("displayName", ""),
        })
    return out


# --- Google -----------------------------------------------------------------
def _g_messages(token: str, limit: int = 10) -> list[dict]:
    lst = httpx.get(f"{GMAIL}/messages?maxResults={limit}&q=newer_than:1d",
                    headers=_auth(token), timeout=20)
    lst.raise_for_status()
    out = []
    for ref in lst.json().get("messages", [])[:limit]:
        md = httpx.get(f"{GMAIL}/messages/{ref['id']}?format=metadata"
                       "&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
                       headers=_auth(token), timeout=20)
        if md.status_code != 200:
            continue
        data = md.json()
        headers = {h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])}
        out.append({
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", "(sin asunto)"),
            "received": headers.get("Date", ""),
            "preview": (data.get("snippet", "") or "")[:240],
            "unread": "UNREAD" in data.get("labelIds", []),
        })
    return out


def _g_events(token: str, limit: int = 15) -> list[dict]:
    now = datetime.utcnow()
    end = now + timedelta(days=1)
    params = {
        "timeMin": now.isoformat() + "Z", "timeMax": end.isoformat() + "Z",
        "singleEvents": "true", "orderBy": "startTime", "maxResults": str(limit),
    }
    r = httpx.get(GCAL, headers=_auth(token), params=params, timeout=20)
    r.raise_for_status()
    out = []
    for e in r.json().get("items", []):
        out.append({
            "subject": e.get("summary", "(sin título)"),
            "start": (e.get("start", {}) or {}).get("dateTime", "") or (e.get("start", {}) or {}).get("date", ""),
            "end": (e.get("end", {}) or {}).get("dateTime", "") or (e.get("end", {}) or {}).get("date", ""),
            "location": e.get("location", ""),
        })
    return out


# --- Generic IMAP (Yahoo, iCloud, Zoho, hosting/corporate, …) ---------------
def imap_test(host: str, port: int, email_addr: str, password: str) -> bool:
    """Try to log in; raise on failure so the caller can report a clear error."""
    import imaplib
    m = imaplib.IMAP4_SSL(host, int(port or 993))
    try:
        m.login(email_addr, password)
        m.select("INBOX", readonly=True)
        return True
    finally:
        try:
            m.logout()
        except Exception:
            pass


def _imap_messages(blob: str, limit: int = 8) -> list[dict]:
    import email as emaillib
    import imaplib
    import json as _json
    from email.header import decode_header, make_header

    cfg = _json.loads(blob)
    m = imaplib.IMAP4_SSL(cfg["host"], int(cfg.get("port", 993)))
    out: list[dict] = []
    try:
        m.login(cfg["email"], cfg["password"])
        m.select("INBOX", readonly=True)
        typ, data = m.search(None, "ALL")
        ids = data[0].split()[-limit:] if data and data[0] else []
        typ, unseen = m.search(None, "UNSEEN")
        unseen_ids = set(unseen[0].split()) if unseen and unseen[0] else set()
        for i in reversed(ids):
            typ, msgdata = m.fetch(i, "(RFC822)")
            if typ != "OK" or not msgdata or not msgdata[0]:
                continue
            msg = emaillib.message_from_bytes(msgdata[0][1])
            preview = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            preview = part.get_payload(decode=True).decode(errors="ignore")
                        except Exception:
                            preview = ""
                        break
            else:
                try:
                    preview = msg.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    preview = ""
            out.append({
                "from": str(make_header(decode_header(msg.get("From", "")))),
                "subject": str(make_header(decode_header(msg.get("Subject", "(sin asunto)")))),
                "received": msg.get("Date", ""),
                "preview": " ".join(preview.split())[:240],
                "unread": i in unseen_ids,
            })
    finally:
        try:
            m.logout()
        except Exception:
            pass
    return out


def fetch(provider: str, token: str) -> dict:
    """Return {messages, events}; never raises — partial data on API errors.

    For OAuth providers `token` is the access token; for IMAP it is the encrypted
    connection blob (already decrypted by the caller). IMAP has no calendar.
    """
    messages: list[dict] = []
    events: list[dict] = []
    try:
        if provider == "microsoft":
            messages = _ms_messages(token)
        elif provider == "google":
            messages = _g_messages(token)
        elif provider == "imap":
            messages = _imap_messages(token)
    except Exception:
        messages = []
    try:
        if provider == "microsoft":
            events = _ms_events(token)
        elif provider == "google":
            events = _g_events(token)
    except Exception:
        events = []
    return {"messages": messages, "events": events}


def render_context(data: dict) -> list[str]:
    """Turn fetched mail/events into context chunks for the model."""
    chunks: list[str] = []
    if data.get("messages"):
        lines = [f"- [{'NO LEÍDO' if m['unread'] else 'leído'}] De {m['from']} — "
                 f"{m['subject']}: {m['preview']}" for m in data["messages"]]
        chunks.append("Correos recientes:\n" + "\n".join(lines))
    if data.get("events"):
        lines = [f"- {e['start']} {e['subject']}"
                 + (f" @ {e['location']}" if e["location"] else "") for e in data["events"]]
        chunks.append("Eventos próximos (hoy):\n" + "\n".join(lines))
    return chunks


_INSTR = {
    "Resumen diario": ("Haz un resumen ejecutivo del día: lo más importante de los correos "
                       "y los eventos de la agenda, con prioridades y pendientes."),
    "Horario del día": "Ordena cronológicamente los eventos del día y señala los huecos libres.",
    "Pendientes por responder": ("Lista los correos que esperan respuesta, priorizados, con una "
                                 "sugerencia breve de acción para cada uno."),
}


def summarize(session, tenant, data: dict, output_type: str) -> dict:
    """Summarize fetched mail/events through the privacy router + model fallback."""
    from ..ai.resilience import generate_with_fallback
    from ..ai.router import route_request

    context = render_context(data)
    if not context:
        return {"content": "", "route": "", "empty": True}
    instruction = _INSTR.get(output_type, _INSTR["Resumen diario"])
    system = ("Eres un asistente ejecutivo. Resume correo y agenda en español, claro y accionable. "
              "No inventes; usa solo lo provisto.")
    decision = route_request(tenant, None, instruction, context, task="recipe")
    gen = generate_with_fallback(decision.route, system, instruction, decision.context or context)
    return {
        "content": gen.response.content,
        "route": gen.route.value,
        "counts": {"messages": len(data.get("messages", [])), "events": len(data.get("events", []))},
    }
