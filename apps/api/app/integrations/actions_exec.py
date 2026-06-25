"""Execute Google Workspace / Microsoft 365 toolkit actions via the user's OAuth
access token. Each function performs one real API call and returns a short detail
string; raises on failure so the caller can mark the request failed.
"""
from __future__ import annotations

import base64
from email.message import EmailMessage

import httpx

GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 25


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _rows(values) -> list[list[str]]:
    """Normalize a Sheets 'values' input (string or list) to a single row."""
    if isinstance(values, list):
        return [[str(v) for v in values]]
    return [[c.strip() for c in str(values or "").split(",")]]


def execute(action_id: str, token: str, params: dict) -> str:
    p = params or {}

    # --- Google ---
    if action_id == "gmail.send":
        msg = EmailMessage()
        msg["To"] = p.get("to", "")
        msg["Subject"] = p.get("subject", "")
        msg.set_content(p.get("body", ""))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        r = httpx.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                       headers=_auth(token), json={"raw": raw}, timeout=TIMEOUT)
        r.raise_for_status()
        return f"Correo enviado a {p.get('to','')}"

    if action_id == "gcal.create_event":
        body = {"summary": p.get("summary", ""),
                "start": {"dateTime": p.get("start", "")},
                "end": {"dateTime": p.get("end", "")}}
        if p.get("location"):
            body["location"] = p["location"]
        r = httpx.post("https://www.googleapis.com/calendar/v3/calendars/primary/events",
                       headers=_auth(token), json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return f"Evento creado: {p.get('summary','')}"

    if action_id == "gsheets.append":
        sid = p.get("spreadsheet_id", "")
        rng = p.get("range", "A1")
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values/{rng}:append"
        r = httpx.post(url, headers=_auth(token), params={"valueInputOption": "USER_ENTERED"},
                       json={"values": _rows(p.get("values"))}, timeout=TIMEOUT)
        r.raise_for_status()
        return f"Fila agregada a la hoja {sid}"

    # --- Microsoft 365 ---
    if action_id == "outlook.send":
        body = {"message": {
            "subject": p.get("subject", ""),
            "body": {"contentType": "Text", "content": p.get("body", "")},
            "toRecipients": [{"emailAddress": {"address": a.strip()}} for a in str(p.get("to", "")).split(",") if a.strip()],
        }, "saveToSentItems": True}
        r = httpx.post(f"{GRAPH}/me/sendMail", headers=_auth(token), json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return f"Correo enviado a {p.get('to','')}"

    if action_id == "mscal.create_event":
        body = {"subject": p.get("summary", ""),
                "start": {"dateTime": p.get("start", ""), "timeZone": "UTC"},
                "end": {"dateTime": p.get("end", ""), "timeZone": "UTC"}}
        if p.get("location"):
            body["location"] = {"displayName": p["location"]}
        r = httpx.post(f"{GRAPH}/me/events", headers=_auth(token), json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return f"Evento creado: {p.get('summary','')}"

    if action_id == "teams.post":
        team, channel = p.get("team_id", ""), p.get("channel_id", "")
        r = httpx.post(f"{GRAPH}/teams/{team}/channels/{channel}/messages",
                       headers=_auth(token), json={"body": {"content": p.get("message", "")}}, timeout=TIMEOUT)
        r.raise_for_status()
        return "Mensaje publicado en Teams"

    raise ValueError(f"Acción no ejecutable: {action_id}")
